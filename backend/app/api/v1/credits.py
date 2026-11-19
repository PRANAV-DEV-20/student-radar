from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.credit import CreditTransaction
from app.models.dossier import ProjectDossier
from app.models.user import User
from app.schemas.credit import (
    CreditBalanceResponse,
    CreditHistoryResponse,
    CreditTransactionResponse,
    PeerReviewRequest,
    PeerReviewResponse,
)
from app.schemas.pr import PRBoostResponse
from app.services.credit_service import (
    ActiveBoostError,
    CreditError,
    DuplicateReviewError,
    InsufficientCreditsError,
    NotDossierOwnerError,
    credit_service,
)

router = APIRouter(prefix="/credits", tags=["Visibility Credits (⚡)"])


@router.get("/balance", response_model=CreditBalanceResponse)
async def get_user_credits_balance(current_user: User = Depends(get_current_user)):
    return CreditBalanceResponse(
        user_id=current_user.id,
        credits_balance=current_user.credits_balance,
    )


@router.get("/transactions", response_model=CreditHistoryResponse)
async def get_credit_transactions(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    transactions: List[CreditTransaction] = await credit_service.get_history(
        db, current_user.id, limit=limit
    )
    return CreditHistoryResponse(
        user_id=current_user.id,
        credits_balance=current_user.credits_balance,
        transactions=[
            CreditTransactionResponse.model_validate(tx) for tx in transactions
        ],
    )


@router.post("/review", response_model=PeerReviewResponse, status_code=status.HTTP_201_CREATED)
async def submit_peer_review(
    req: PeerReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submits a substantive 3-field peer review (Strength, Bottleneck, Suggestion).
    The 80-character anti-spam floor is enforced by ``PeerReviewRequest``.
    Awards +10⚡ once per reviewer per dossier.
    """
    result = await db.execute(select(ProjectDossier).where(ProjectDossier.id == req.dossier_id))
    dossier = result.scalars().first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found.")

    rubric = {
        "strength": req.rubric.strength,
        "bottleneck": req.rubric.bottleneck,
        "suggestion": req.rubric.suggestion,
    }

    try:
        new_balance = await credit_service.record_peer_review(
            db, current_user, dossier, rubric
        )
        await db.commit()
    except DuplicateReviewError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InsufficientCreditsError as exc:  # pragma: no cover - review awards credits
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except CreditError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PeerReviewResponse(
        status="review_accepted",
        dossier_id=dossier.id,
        credits_awarded=settings.PEER_REVIEW_CREDITS,
        new_balance=new_balance,
    )


@router.post("/boost/{dossier_id}", response_model=PRBoostResponse)
async def boost_dossier_with_credits(
    dossier_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deduct 20⚡ and activate a 48-hour visibility boost on a dossier."""
    result = await db.execute(
        select(ProjectDossier)
        .where(ProjectDossier.id == dossier_id)
        .with_for_update()
    )
    dossier = result.scalars().first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found.")

    try:
        payload = await credit_service.boost_dossier(db, current_user, dossier)
        await db.commit()
    except InsufficientCreditsError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotDossierOwnerError as exc:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ActiveBoostError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except CreditError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PRBoostResponse(**payload)
