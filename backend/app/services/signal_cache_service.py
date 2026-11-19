"""Persistence helpers for external signal snapshots."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.dossier import ProjectDossier
from app.models.signal_cache import SignalCache
from app.schemas.signals import MarketIntelligenceResponse
from app.services.external_intelligence import external_intelligence

logger = logging.getLogger(__name__)


def cache_key(
    keywords: Sequence[str],
    persona: str,
    title: Optional[str] = None,
    max_per_source: int = 3,
) -> str:
    raw = "|".join(
        [
            persona.strip().lower(),
            (title or "").strip().lower(),
            str(max_per_source),
            ",".join(sorted(item.strip().lower() for item in keywords if item.strip())),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:64]


def _provider_label() -> str:
    if settings.TAVILY_API_KEY:
        return "tavily"
    if settings.EXA_API_KEY:
        return "exa"
    return "none"


def _ttl() -> timedelta:
    return timedelta(minutes=max(5, settings.SIGNAL_CACHE_TTL_MINUTES))


async def _upsert_payload(
    db: AsyncSession, key: str, result: MarketIntelligenceResponse
) -> None:
    now = datetime.now(timezone.utc)
    entry = SignalCache(
        cache_key=key,
        payload=result.model_dump(mode="json"),
        provider=_provider_label(),
        is_live=any(signal.is_live for signal in result.signals),
        generated_at=result.generated_at or now,
        expires_at=now + _ttl(),
    )
    await db.merge(entry)


async def get_or_collect(
    db: AsyncSession,
    keywords: Sequence[str],
    persona: str,
    title: Optional[str] = None,
    max_per_source: Optional[int] = None,
) -> MarketIntelligenceResponse:
    """Serve a fresh snapshot when possible, otherwise collect and persist one."""

    per_source = max_per_source or settings.EXTERNAL_SIGNAL_MAX_PER_SOURCE
    key = cache_key(keywords, persona, title, per_source)
    now = datetime.now(timezone.utc)

    try:
        cached = await db.get(SignalCache, key)
        if cached and cached.expires_at:
            expires_at = cached.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at > now and isinstance(cached.payload, dict):
                return MarketIntelligenceResponse(**cached.payload)
    except Exception as exc:  # pragma: no cover - missing table / DB outage
        logger.warning("Signal cache read failed, collecting live instead: %s", exc)
        await db.rollback()

    result = await external_intelligence.collect_signals(
        keywords=keywords,
        domain_persona=persona,
        title=title,
        max_per_source=per_source,
    )

    try:
        await _upsert_payload(db, key, result)
        await db.commit()
    except Exception as exc:  # pragma: no cover - missing table / DB outage
        logger.warning("Signal cache write failed: %s", exc)
        await db.rollback()

    return result


async def refresh_all(db: AsyncSession) -> Dict[str, int]:
    """Refresh default snapshots for every persona and active dossier keywords."""

    requests: List[Dict[str, Any]] = []
    for persona in settings.KNOWN_PERSONAS:
        requests.append(
            {
                "keywords": [persona.replace("_", " ")],
                "persona": persona,
                "title": None,
            }
        )

    dossier_result = await db.execute(
        select(ProjectDossier.tech_stack, ProjectDossier.domain_persona)
        .order_by(ProjectDossier.created_at.desc())
        .limit(25)
    )
    for tech_stack, persona in dossier_result.all():
        keywords = [str(item) for item in (tech_stack or [])[:5] if str(item).strip()]
        if not keywords:
            continue
        requests.append(
            {
                "keywords": keywords,
                "persona": persona or settings.DEFAULT_PERSONA,
                "title": None,
            }
        )

    refreshed = 0
    live_snapshots = 0
    for request in requests:
        per_source = settings.EXTERNAL_SIGNAL_MAX_PER_SOURCE
        key = cache_key(
            request["keywords"], request["persona"], request.get("title"), per_source
        )
        result = await external_intelligence.collect_signals(
            keywords=request["keywords"],
            domain_persona=request["persona"],
            title=request.get("title"),
            max_per_source=per_source,
        )
        await _upsert_payload(db, key, result)
        refreshed += 1
        if any(signal.is_live for signal in result.signals):
            live_snapshots += 1

    await db.commit()
    return {"requests": len(requests), "refreshed": refreshed, "live": live_snapshots}
