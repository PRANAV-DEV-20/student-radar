from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.dossier import ProjectDossier
from app.schemas.matchmaking import CoBuilderMatchResponse
from app.services.matchmaker import matchmaker

router = APIRouter(prefix="/matchmaking", tags=["Co-Builder Matchmaking"])


@router.get("/cobuilders/{dossier_id}", response_model=CoBuilderMatchResponse)
async def get_complementary_cobuilders(
    dossier_id: UUID,
    limit: int = Query(default=settings.MATCHMAKING_LIMIT, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Return top complementary co-builders ranked by skill-gap fit."""
    result = await db.execute(select(ProjectDossier).where(ProjectDossier.id == dossier_id))
    dossier = result.scalars().first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found.")

    return await matchmaker.match_cobuilders(db, dossier, limit=limit)
