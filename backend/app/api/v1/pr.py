import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import User
from app.models.dossier import ProjectDossier
from app.models.pr_asset import PRAsset
from app.models.credit import CreditTransaction
from app.schemas.pr import (
    PRGenerateRequest,
    PRGenerateResponse,
    PRBoostResponse
)
from app.services.pr_strategist import pr_strategist
from app.services.card_renderer import card_renderer
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/pr", tags=["PR Studio"])

@router.post("/generate", response_model=PRGenerateResponse)
async def generate_pr_copy(
    req: PRGenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(ProjectDossier).where(ProjectDossier.id == req.dossier_id))
    dossier = result.scalars().first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found.")

    dossier_dict = {
        "title": dossier.title,
        "tagline": dossier.tagline,
        "domain_persona": dossier.domain_persona,
        "problem_statement": dossier.problem_statement,
        "solution_breakdown": dossier.solution_breakdown,
        "tech_stack": dossier.tech_stack,
        "key_metrics": dossier.key_metrics,
        "slug": dossier.slug
    }

    # Generate PR copy
    pr_result = await pr_strategist.generate_pr_assets(
        dossier=dossier_dict,
        playbook_type=req.playbook_type,
        tone=req.tone,
        target_audience=req.target_audience or "Engineers and Investors"
    )

    # Render OpenGraph card
    og_card_data_uri = card_renderer.generate_card_data_uri(dossier_dict)

    # Persist PR Asset
    pr_asset = PRAsset(
        dossier_id=dossier.id,
        asset_type=req.playbook_type,
        content_json=pr_result,
        og_image_url=og_card_data_uri
    )
    db.add(pr_asset)
    await db.commit()

    return PRGenerateResponse(
        asset_type=req.playbook_type,
        headline=pr_result.get("headline", ""),
        body_markdown=pr_result.get("body_markdown", ""),
        hooks=pr_result.get("hooks", []),
        suggested_tags=pr_result.get("suggested_tags", []),
        og_image_url=og_card_data_uri
    )

@router.post("/{dossier_id}/boost", response_model=PRBoostResponse)
async def boost_dossier_feed(
    dossier_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.credits_balance < 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient Visibility Credits (Required: 20⚡, Current Balance: {current_user.credits_balance}⚡)."
        )

    result = await db.execute(select(ProjectDossier).where(ProjectDossier.id == dossier_id))
    dossier = result.scalars().first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found.")

    current_user.credits_balance -= 20
    dossier.boosted = True

    # Record credit transaction
    transaction = CreditTransaction(
        user_id=current_user.id,
        amount=-20,
        reason="boost_launch",
        metadata_json={"dossier_id": str(dossier.id), "title": dossier.title}
    )
    db.add(transaction)
    await db.commit()

    expires_at = datetime.now(timezone.utc) + timedelta(days=3)
    return PRBoostResponse(
        status="boosted",
        credits_deducted=20,
        remaining_balance=current_user.credits_balance,
        boost_expires_at=expires_at
    )

