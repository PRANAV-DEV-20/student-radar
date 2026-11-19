"""Cross-platform market intelligence endpoints."""

from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.schemas.signals import MarketIntelligenceResponse
from app.services.external_intelligence import SOURCE_LABELS, SUPPORTED_SOURCES
from app.services.signal_cache_service import get_or_collect

router = APIRouter(prefix="/signals", tags=["External Intelligence"])


@router.get("/sources")
async def list_signal_sources():
    return {
        "sources": [
            {"id": source, "label": SOURCE_LABELS[source]}
            for source in SUPPORTED_SOURCES
        ],
        "grounding_providers": [
            name
            for name, key in (
                ("tavily", settings.TAVILY_API_KEY),
                ("exa", settings.EXA_API_KEY),
            )
            if key
        ],
        "grounding_provider_order": ["tavily", "exa"],
    }


@router.get("/market", response_model=MarketIntelligenceResponse)
async def market_intelligence(
    keywords: str = Query(
        default="",
        description="Comma-separated keywords, ideally taken from the active dossier.",
    ),
    persona: str = Query(default=settings.DEFAULT_PERSONA),
    title: Optional[str] = Query(default=None),
    max_per_source: int = Query(default=settings.EXTERNAL_SIGNAL_MAX_PER_SOURCE, ge=1, le=8),
    db: AsyncSession = Depends(get_db),
):
    keyword_list = [item.strip() for item in keywords.split(",") if item.strip()]
    return await get_or_collect(
        db=db,
        keywords=keyword_list,
        persona=persona,
        title=title,
        max_per_source=max_per_source,
    )
