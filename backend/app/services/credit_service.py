"""Atomic Visibility Credits ledger operations.

All balance mutations happen through a single ``UPDATE ... RETURNING``
statement so concurrent requests can never overdraw an account or double-award
a peer review.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.credit import CreditTransaction
from app.models.dossier import ProjectDossier
from app.models.user import User


class CreditError(Exception):
    """Base class for credit-economy failures."""


class InsufficientCreditsError(CreditError):
    def __init__(self, required: int, balance: int):
        self.required = required
        self.balance = balance
        super().__init__(
            f"Insufficient Visibility Credits (Required: {required}⚡, "
            f"Current Balance: {balance}⚡)."
        )


class DuplicateReviewError(CreditError):
    def __init__(self, dossier_id: UUID):
        self.dossier_id = dossier_id
        super().__init__("You have already submitted a peer review for this dossier.")


class ActiveBoostError(CreditError):
    def __init__(self, expires_at: datetime):
        self.expires_at = expires_at
        super().__init__(
            "This dossier already has an active visibility boost "
            f"(expires {expires_at.isoformat()})."
        )


class NotDossierOwnerError(CreditError):
    def __init__(self):
        super().__init__("You can only boost dossiers that you own.")


class CreditService:
    # ------------------------------------------------------------------
    # Public ledger operations
    # ------------------------------------------------------------------
    async def get_balance(self, db: AsyncSession, user_id: UUID) -> int:
        result = await db.execute(select(User.credits_balance).where(User.id == user_id))
        value = result.scalar_one_or_none()
        return int(value or 0)

    async def award_credits(
        self,
        db: AsyncSession,
        user_id: UUID,
        amount: int,
        reason: str,
        *,
        dossier_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        if amount <= 0:
            raise ValueError("Award amount must be positive.")

        result = await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(credits_balance=User.credits_balance + amount)
            .returning(User.credits_balance)
        )
        new_balance = result.scalar_one_or_none()
        if new_balance is None:
            raise CreditError("User not found while awarding credits.")

        db.add(
            CreditTransaction(
                user_id=user_id,
                dossier_id=dossier_id,
                amount=amount,
                reason=reason[:100],
                metadata_json=metadata or {},
            )
        )
        await db.flush()
        return int(new_balance)

    async def spend_credits(
        self,
        db: AsyncSession,
        user_id: UUID,
        amount: int,
        reason: str,
        *,
        dossier_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        if amount <= 0:
            raise ValueError("Spend amount must be positive.")

        result = await db.execute(
            update(User)
            .where(User.id == user_id, User.credits_balance >= amount)
            .values(credits_balance=User.credits_balance - amount)
            .returning(User.credits_balance)
        )
        new_balance = result.scalar_one_or_none()
        if new_balance is None:
            balance = await self.get_balance(db, user_id)
            raise InsufficientCreditsError(amount, balance)

        db.add(
            CreditTransaction(
                user_id=user_id,
                dossier_id=dossier_id,
                amount=-amount,
                reason=reason[:100],
                metadata_json=metadata or {},
            )
        )
        await db.flush()
        return int(new_balance)

    # ------------------------------------------------------------------
    # Peer review (+10⚡, once per reviewer per dossier)
    # ------------------------------------------------------------------
    async def record_peer_review(
        self,
        db: AsyncSession,
        reviewer: User,
        dossier: ProjectDossier,
        rubric: Dict[str, str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        if dossier.user_id is not None and dossier.user_id == reviewer.id:
            raise CreditError("You cannot submit a peer review for your own dossier.")

        existing = await db.execute(
            select(CreditTransaction.id).where(
                CreditTransaction.user_id == reviewer.id,
                CreditTransaction.dossier_id == dossier.id,
                CreditTransaction.reason == "review_peer",
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateReviewError(dossier.id)

        payload: Dict[str, Any] = {
            "dossier_title": dossier.title,
            "rubric": rubric,
        }
        if metadata:
            payload.update(metadata)

        try:
            return await self.award_credits(
                db,
                reviewer.id,
                settings.PEER_REVIEW_CREDITS,
                "review_peer",
                dossier_id=dossier.id,
                metadata=payload,
            )
        except IntegrityError as exc:  # guarded by the partial unique index
            await db.rollback()
            raise DuplicateReviewError(dossier.id) from exc

    # ------------------------------------------------------------------
    # Boost (-20⚡ for BOOST_DURATION_HOURS)
    # ------------------------------------------------------------------
    async def boost_dossier(
        self,
        db: AsyncSession,
        user: User,
        dossier: ProjectDossier,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)

        # Seeded/demo dossiers are intentionally unowned and may be boosted by
        # any authenticated user. Real dossiers are owner-only.
        if dossier.user_id is not None and dossier.user_id != user.id:
            raise NotDossierOwnerError()

        if dossier.boosted_until is not None:
            expires_at = dossier.boosted_until
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if dossier.boosted and expires_at > now:
                raise ActiveBoostError(expires_at)

        expires_at = now + timedelta(hours=settings.BOOST_DURATION_HOURS)
        new_balance = await self.spend_credits(
            db,
            user.id,
            settings.BOOST_COST_CREDITS,
            "boost_launch",
            dossier_id=dossier.id,
            metadata={
                "dossier_title": dossier.title,
                "dossier_slug": dossier.slug,
                "boost_expires_at": expires_at.isoformat(),
            },
        )

        dossier.boosted = True
        dossier.boosted_until = expires_at
        await db.flush()

        return {
            "status": "boosted",
            "dossier_id": dossier.id,
            "credits_deducted": settings.BOOST_COST_CREDITS,
            "remaining_balance": new_balance,
            "boost_expires_at": expires_at,
        }

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------
    async def get_history(
        self, db: AsyncSession, user_id: UUID, limit: int = 50
    ) -> List[CreditTransaction]:
        result = await db.execute(
            select(CreditTransaction)
            .where(CreditTransaction.user_id == user_id)
            .order_by(CreditTransaction.created_at.desc())
            .limit(max(1, min(limit, 200)))
        )
        return list(result.scalars().all())


credit_service = CreditService()
