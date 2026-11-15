import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import User
from app.models.dossier import ProjectDossier
from app.models.credit import CreditTransaction
from app.schemas.credit import (
    PeerReviewRequest,
    PeerReviewResponse,
    CreditBalanceResponse
)
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/credits", tags=["Visibility Credits (⚡)"])

@router.get("/balance", response_model=CreditBalanceResponse)
async def get_user_credits_balance(current_user: User = Depends(get_current_user)):
    return CreditBalanceResponse(
        user_id=current_user.id,
        credits_balance=current_user.credits_balance
    )

@router.post("/review", response_model=PeerReviewResponse, status_code=status.HTTP_201_CREATED)
async def submit_peer_review(
    req: PeerReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submits a substantive 3-field peer review (Strength, Bottleneck, Suggestion).
    Must pass minimum 80-character validation to prevent spam.
    Awards +10⚡ credits to reviewer.
    """
    result = await db.execute(select(ProjectDossier).where(ProjectDossier.id == req.dossier_id))
    dossier = result.scalars().first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found.")

    if dossier.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot submit a peer review for your own dossier.")

    current_user.credits_balance += 10

    transaction = CreditTransaction(
        user_id=current_user.id,
        amount=10,
        reason="review_peer",
        metadata_json={
            "dossier_id": str(dossier.id),
            "strength": req.rubric.strength,
            "bottleneck": req.rubric.bottleneck,
            "suggestion": req.rubric.suggestion
        }
    )
    db.add(transaction)
    await db.commit()

    return PeerReviewResponse(
        status="review_accepted",
        credits_awarded=10,
        new_balance=current_user.credits_balance
    )

