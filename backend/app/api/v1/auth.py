import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.models.dossier import ProjectDossier
from app.models.network import ReferralInvite
from app.models.user import User
from app.schemas.auth import (
    ClaimGuestRequest,
    ClaimGuestResponse,
    GoogleAuthRequest,
    TokenResponse,
    UserLoginRequest,
    UserProfileResponse,
    UserRegisterRequest,
    UserUpdateRequest,
)
from app.services.credit_service import credit_service
from app.services.gemini_client import gemini_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication & Guest Claim"])


# ----------------------------------------------------------------------
# Dependencies
# ----------------------------------------------------------------------
async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    subject = decode_access_token(token)
    if not subject:
        return None
    try:
        user_id = uuid.UUID(str(subject))
    except (ValueError, TypeError, AttributeError):
        # Never send a non-UUID string into a UUID column.
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


async def get_current_user(
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
async def claim_guest_dossiers(
    db: AsyncSession, user: User, guest_session_id: Optional[str]
) -> int:
    """Attach every dossier created by a guest browser session to ``user``."""
    guest_session_id = (guest_session_id or "").strip()
    if not guest_session_id:
        return 0
    result = await db.execute(
        update(ProjectDossier)
        .where(ProjectDossier.guest_session_id == guest_session_id)
        .values(user_id=user.id, guest_session_id=None)
    )
    return int(result.rowcount or 0)


async def _award_referral_if_present(
    db: AsyncSession, user: User, referral_token: Optional[str]
) -> int:
    """Award the inviter once when a referred student signs up.

    The invite row is locked with ``FOR UPDATE`` so two concurrent signups
    using the same token cannot both claim it.
    """
    token = (referral_token or "").strip()
    if not token:
        return 0
    result = await db.execute(
        select(ReferralInvite)
        .where(ReferralInvite.token == token)
        .with_for_update()
    )
    invite = result.scalars().first()
    if not invite or invite.status != "pending":
        return 0
    if invite.sender_user_id == user.id:
        return 0

    invite.status = "claimed"
    invite.claimed_user_id = user.id
    await credit_service.award_credits(
        db,
        invite.sender_user_id,
        settings.REFERRAL_SIGNUP_CREDITS,
        "signup_referral",
        metadata={
            "referral_token": token,
            "referred_user_id": str(user.id),
        },
    )
    return settings.REFERRAL_SIGNUP_CREDITS


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        credits_balance=user.credits_balance,
    )


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    email = str(req.email).strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    try:
        hashed_password = get_password_hash(req.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    new_user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=req.full_name,
        campus_or_org=req.campus_or_org,
        city=req.city or settings.DEFAULT_CITY,
        active_persona_id=req.active_persona_id or settings.DEFAULT_PERSONA,
        verified_skills=req.verified_skills or [],
        credits_balance=settings.SIGNUP_CREDITS,
    )

    if new_user.verified_skills:
        embedding_text = " ".join(new_user.verified_skills)
        new_user.skills_embedding = await gemini_service.generate_embedding(embedding_text)

    db.add(new_user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail="An account with this email already exists.") from exc

    await claim_guest_dossiers(db, new_user, req.guest_session_id)
    await _award_referral_if_present(db, new_user, req.referral_token)

    await db.commit()
    await db.refresh(new_user)
    return _token_response(new_user)


@router.post("/login", response_model=TokenResponse)
async def login(req: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    email = str(req.email).strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user or not user.hashed_password or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    await claim_guest_dossiers(db, user, req.guest_session_id)
    await db.commit()
    await db.refresh(user)
    return _token_response(user)


@router.post("/google", response_model=TokenResponse)
async def google_auth(req: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """Simulated/live Google OAuth handler; automatically binds guest session ID.

    A production deployment should verify ``id_token`` against Google's JWKS.
    The simulated development flow keeps the endpoint usable without external
    credentials while preserving the exact same session-merging behaviour.
    """
    simulated_email = settings.SIMULATED_OAUTH_EMAIL.strip().lower()
    result = await db.execute(select(User).where(User.email == simulated_email))
    user = result.scalars().first()
    created = False

    if not user:
        user = User(
            email=simulated_email,
            full_name="Student Builder",
            oauth_provider="google",
            campus_or_org="Pune Institute of Technology",
            city=settings.DEFAULT_CITY,
            active_persona_id=settings.DEFAULT_PERSONA,
            verified_skills=[],
            credits_balance=settings.SIGNUP_CREDITS,
        )
        db.add(user)
        try:
            await db.flush()
            created = True
        except IntegrityError:
            await db.rollback()
            result = await db.execute(select(User).where(User.email == simulated_email))
            user = result.scalars().first()
            if not user:
                raise

    await claim_guest_dossiers(db, user, req.guest_session_id)
    # Referral credit is a signup reward, not a login reward.
    if created:
        await _award_referral_if_present(db, user, req.referral_token)
    await db.commit()
    await db.refresh(user)
    return _token_response(user)


@router.post("/claim-guest", response_model=ClaimGuestResponse)
async def claim_guest_session(
    req: ClaimGuestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    claimed_count = await claim_guest_dossiers(db, current_user, req.guest_session_id)
    await db.commit()
    await db.refresh(current_user)
    return ClaimGuestResponse(
        status="success",
        claimed_dossiers_count=claimed_count,
        user_id=current_user.id,
        credits_balance=current_user.credits_balance,
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserProfileResponse)
async def update_profile(
    req: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.full_name is not None:
        current_user.full_name = req.full_name
    if req.campus_or_org is not None:
        current_user.campus_or_org = req.campus_or_org
    if req.city is not None:
        current_user.city = req.city
    if req.active_persona_id is not None:
        current_user.active_persona_id = req.active_persona_id
    if req.verified_skills is not None:
        current_user.verified_skills = req.verified_skills
        if req.verified_skills:
            current_user.skills_embedding = await gemini_service.generate_embedding(
                " ".join(req.verified_skills)
            )
        else:
            current_user.skills_embedding = None

    await db.commit()
    await db.refresh(current_user)
    return current_user
