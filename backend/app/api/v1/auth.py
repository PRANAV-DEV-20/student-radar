from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from app.models.user import User
from app.models.dossier import ProjectDossier
from app.schemas.auth import (
    TokenResponse,
    UserRegisterRequest,
    UserLoginRequest,
    ClaimGuestRequest,
    ClaimGuestResponse,
    GoogleAuthRequest
)

router = APIRouter(prefix="/auth", tags=["Authentication & Guest Claim"])

async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1]
    user_id = decode_access_token(token)
    if not user_id:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()

async def get_current_user(
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> User:
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required."
        )
    return current_user

@router.post("/register", response_model=TokenResponse)
async def register(req: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email.lower()))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    new_user = User(
        email=req.email.lower(),
        hashed_password=get_password_hash(req.password),
        full_name=req.full_name,
        credits_balance=50
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Claim guest sessions if present
    if req.guest_session_id:
        await db.execute(
            update(ProjectDossier)
            .where(ProjectDossier.guest_session_id == req.guest_session_id)
            .values(user_id=new_user.id, guest_session_id=None)
        )
        await db.commit()

    token = create_access_token(str(new_user.id))
    return TokenResponse(
        access_token=token,
        user_id=new_user.id,
        full_name=new_user.full_name,
        email=new_user.email,
        credits_balance=new_user.credits_balance
    )

@router.post("/login", response_model=TokenResponse)
async def login(req: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email.lower()))
    user = result.scalars().first()
    if not user or not user.hashed_password or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if req.guest_session_id:
        await db.execute(
            update(ProjectDossier)
            .where(ProjectDossier.guest_session_id == req.guest_session_id)
            .values(user_id=user.id, guest_session_id=None)
        )
        await db.commit()

    token = create_access_token(str(user.id))
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        credits_balance=user.credits_balance
    )

@router.post("/google", response_model=TokenResponse)
async def google_auth(req: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """Simulated or live Google OAuth handler; automatically binds guest session ID."""
    simulated_email = "student.builder@university.edu"
    result = await db.execute(select(User).where(User.email == simulated_email))
    user = result.scalars().first()

    if not user:
        user = User(
            email=simulated_email,
            full_name="Student Builder",
            oauth_provider="google",
            credits_balance=50
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    if req.guest_session_id:
        await db.execute(
            update(ProjectDossier)
            .where(ProjectDossier.guest_session_id == req.guest_session_id)
            .values(user_id=user.id, guest_session_id=None)
        )
        await db.commit()

    token = create_access_token(str(user.id))
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        credits_balance=user.credits_balance
    )

@router.post("/claim-guest", response_model=ClaimGuestResponse)
async def claim_guest_session(
    req: ClaimGuestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        update(ProjectDossier)
        .where(ProjectDossier.guest_session_id == req.guest_session_id)
        .values(user_id=current_user.id, guest_session_id=None)
    )
    await db.commit()
    claimed_count = result.rowcount or 0

    return ClaimGuestResponse(
        status="success",
        claimed_dossiers_count=claimed_count,
        user_id=current_user.id,
        credits_balance=current_user.credits_balance
    )

