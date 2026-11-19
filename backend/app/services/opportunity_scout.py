"""Persona-driven opportunity scouting with two-pass deduplication.

Live scouting uses Gemini Search Grounding (with Tavily as the event-search
fallback) when configured. Without keys or on network failure, the service
returns real, openable search URLs marked ``is_live=False`` so the scheduled
radar never invents an event, deadline, reward, or organiser.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.opportunity import Opportunity
from app.services.dedup_service import dedup_service
from app.services.gemini_client import gemini_service

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "configs" / "personas"
_DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})")
_REWARD_PATTERN = re.compile(r"(?:US)?\$\s?[\d,.]+(?:\s?(?:k|m|million|stipend))?", re.IGNORECASE)


def _persona_configs() -> List[Dict[str, Any]]:
    configs: List[Dict[str, Any]] = []
    for path in sorted(_CONFIG_DIR.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as handle:
                configs.append(json.load(handle))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not load persona config %s: %s", path, exc)
    return configs


def _parse_deadline(text: str, fallback_days: int = 14) -> Tuple[datetime, bool]:
    now = datetime.now(timezone.utc)
    match = _DATE_PATTERN.search(text or "")
    if match:
        try:
            parsed = datetime.strptime(match.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if parsed > now:
                return parsed.replace(hour=23, minute=59), False
        except ValueError:
            pass
    return now + timedelta(days=fallback_days), True


def _infer_category(title: str, description: str) -> str:
    blob = f"{title} {description}".lower()
    if any(word in blob for word in ("hackathon", "build sprint", "buildathon", "hack")):
        return "hackathon"
    if any(word in blob for word in ("grant", "funding", "prize")):
        return "grant"
    if any(word in blob for word in ("fellowship", "residency")):
        return "fellowship"
    return "general_event"


def _authority(url: str) -> int:
    host = urllib.parse.urlsplit(url).hostname or ""
    host = host.lower().removeprefix("www.")
    trusted = (
        "devpost.com",
        "devfolio.co",
        "unstop.com",
        "lu.ma",
        "arxiv.org",
        "nsf.gov",
        "gov.in",
        "europa.eu",
    )
    if host.endswith(trusted):
        return 3
    if host.endswith((".gov", ".edu", ".org")):
        return 2
    return 1


def _fallback_search_links() -> List[Dict[str, Any]]:
    """Return real search links instead of invented events.

    These rows are discovery aids, not opportunities. They are explicitly
    marked ``is_live=False`` and carry no organiser, deadline, or reward claim
    beyond the synthetic sort key required by the current schema.
    """

    links: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for config in _persona_configs():
        persona = str(config.get("persona_id") or settings.DEFAULT_PERSONA)
        queries = list(config.get("radar_query_templates") or [])
        query = queries[0] if queries else f"{persona.replace('_', ' ')} hackathon grant fellowship"
        url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
        if url in seen:
            continue
        seen.add(url)
        links.append(
            {
                "title": f"Verify open {persona.replace('_', ' ')} opportunities",
                "category": "general_event",
                "canonical_source_url": url,
                "host_organization": None,
                # Sorting key only. The UI treats this as unverified via metadata.
                "deadline": datetime.now(timezone.utc) + timedelta(days=14),
                "description": (
                    "Verification link only. No event details, deadlines, rewards, or "
                    "organisers were inferred. Open the search results to confirm them."
                ),
                "tags": list(config.get("recommended_tags", []))[:6],
                "domain_personas": [persona],
                "location_type": "virtual",
                "reward_pool": None,
                "decision_metadata": {
                    "source": "search_link",
                    "is_live": False,
                    "deadline_inferred": True,
                },
            }
        )
    return links


def _tavily_results(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not settings.TAVILY_API_KEY:
        return []
    queries = config.get("radar_query_templates") or []
    persona = config.get("persona_id", settings.DEFAULT_PERSONA)
    results: List[Dict[str, Any]] = []
    try:
        with httpx.Client(timeout=8.0) as client:
            for query in queries[:4]:
                response = client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": settings.TAVILY_API_KEY,
                        "query": query,
                        "search_depth": "basic",
                        "include_answer": True,
                        "max_results": 5,
                    },
                )
                if response.status_code != 200:
                    continue
                for item in response.json().get("results", []):
                    title = str(item.get("title") or "").strip()
                    url = str(item.get("url") or "").strip()
                    if not title or not url:
                        continue
                    description = str(item.get("content") or item.get("snippet") or "").strip()
                    deadline, inferred = _parse_deadline(description)
                    category = _infer_category(title, description)
                    results.append(
                        {
                            "title": title[:250],
                            "category": category,
                            "canonical_source_url": url,
                            "host_organization": urllib.parse.urlsplit(url).hostname,
                            "deadline": deadline,
                            "description": description[:4000] or title,
                            "tags": list(config.get("recommended_tags", []))[:6],
                            "domain_personas": [persona],
                            "location_type": "virtual",
                            "reward_pool": (_REWARD_PATTERN.search(description).group(0) if _REWARD_PATTERN.search(description) else None),
                            "decision_metadata": {
                                "deadline_inferred": inferred,
                                "source": "tavily",
                                "is_live": True,
                            },
                        }
                    )
    except (httpx.HTTPError, OSError, ValueError) as exc:
        logger.warning("Tavily scout failed: %s", exc)
    return results


def _gemini_grounded_results(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch events through Gemini Search Grounding when a key is configured."""

    if not settings.GEMINI_API_KEY:
        return []

    queries = list(config.get("radar_query_templates") or [])
    query = queries[0] if queries else str(config.get("persona_id", "student")).replace("_", " ")
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        # This helper is only used by the synchronous Celery path. Never create
        # a nested event loop if a caller happens to already be async.
        return []

    try:
        events = asyncio.run(gemini_service.search_grounded_events(query, str(config.get("persona_id"))))
    except Exception as exc:  # pragma: no cover - network/SDK dependent
        logger.warning("Gemini grounded scout failed: %s", exc)
        return []

    recommended = list(config.get("recommended_tags", []))[:6]
    for event in events:
        if not event.get("tags"):
            event["tags"] = recommended
    return events


def collect_candidates() -> List[Dict[str, Any]]:
    """Scheduled 5:30 AM crawl using the same intent/recency pipeline as live scans.

    Only the hackathons/grants intent produces opportunity rows. News and
    builder results stay in the signal feed, and verification links are never
    persisted as Radar cards.
    """

    from app.services.radar_live_service import (
        _to_opportunity_candidate,
        build_project_context,
        collect_intent_candidates,
    )

    candidates: List[Dict[str, Any]] = []
    by_url: Dict[str, Dict[str, Any]] = {}

    def add(item: Dict[str, Any]) -> None:
        url = item["canonical_source_url"]
        existing = by_url.get(url)
        if existing is not None:
            for tag in item.get("tags") or []:
                if tag not in existing["tags"]:
                    existing["tags"].append(tag)
            for persona_id in item.get("domain_personas") or []:
                if persona_id not in existing["domain_personas"]:
                    existing["domain_personas"].append(persona_id)
            return
        item.setdefault("tags", [])
        item.setdefault("domain_personas", [])
        by_url[url] = item
        candidates.append(item)

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        # Sync Celery helper only. Live scans call the async service directly.
        return []

    scanned_at = datetime.now(timezone.utc)
    for config in _persona_configs():
        persona = str(config.get("persona_id") or settings.DEFAULT_PERSONA)
        context = build_project_context(None, None, persona)
        query = f"{context['persona_label']} hackathon OR buildathon registration open 2026"
        try:
            result = asyncio.run(
                collect_intent_candidates(
                    context=context,
                    persona=persona,
                    intent="hackathons",
                    query=query,
                    language=settings.RADAR_SCAN_LANGUAGE,
                    max_age_hours=0,
                    keywords=list(context.get("tech_stack") or []),
                )
            )
        except Exception as exc:  # pragma: no cover - provider/network dependent
            logger.warning("Scheduled Radar intent scan failed for %s: %s", persona, exc)
            continue

        for item in result.items:
            candidate = _to_opportunity_candidate(
                item,
                persona=persona,
                tags=list(config.get("recommended_tags") or [])[:6],
                scanned_at=scanned_at,
            )
            if candidate:
                add(candidate)
    return candidates


async def upsert_candidates(
    db: AsyncSession, candidates: List[Dict[str, Any]]
) -> Dict[str, int]:
    """Insert new opportunities and merge cross-posted duplicates."""
    now = datetime.now(timezone.utc)
    inserted = 0
    merged = 0
    skipped = 0

    for candidate in candidates:
        deadline = candidate.get("deadline")
        if deadline is None or deadline <= now:
            skipped += 1
            continue

        title = str(candidate["title"]).strip()
        url = str(candidate["canonical_source_url"]).strip()
        fingerprint = dedup_service.compute_sha256_fingerprint(url, title)
        emb_text = f"{title}: {candidate.get('description', '')}"
        embedding = await gemini_service.generate_embedding(emb_text)

        # Pass 1: hard fingerprint / canonical URL.
        existing_result = await db.execute(
            select(Opportunity).where(
                or_(
                    Opportunity.sha256_hash == fingerprint,
                    Opportunity.canonical_source_url == url,
                )
            )
        )
        existing = existing_result.scalars().first()

        # Pass 2: semantic vector duplicate within a 3-day window.
        if existing is None and embedding:
            semantic_result = await db.execute(
                select(Opportunity)
                .where(
                    and_(
                        Opportunity.event_date.is_not(None),
                        func.abs(Opportunity.event_date - deadline.date()) <= 3,
                        Opportunity.embedding.is_not(None),
                        Opportunity.embedding.cosine_distance(embedding) < 0.12,
                    )
                )
                .limit(1)
            )
            existing = semantic_result.scalars().first()

        if existing is not None:
            if _authority(url) > _authority(existing.canonical_source_url):
                existing.canonical_source_url = url
                existing.sha256_hash = fingerprint
            if not existing.description or len(candidate.get("description", "")) > len(existing.description or ""):
                existing.description = candidate.get("description", existing.description)
            if not existing.reward_pool and candidate.get("reward_pool"):
                existing.reward_pool = candidate["reward_pool"]
            if not existing.city and candidate.get("city"):
                existing.city = candidate["city"]
            if not existing.event_date and deadline:
                existing.event_date = candidate.get("event_date") or deadline.date()
            if not existing.host_organization and candidate.get("host_organization"):
                existing.host_organization = candidate["host_organization"]
            if candidate.get("location_type") and candidate["location_type"] != "virtual":
                existing.location_type = candidate["location_type"]

            # Preserve the strongest provenance when the same event is found by
            # a direct adapter after an older search-result row.
            candidate_meta = candidate.get("decision_metadata") or {}
            existing_meta = dict(existing.decision_metadata or {})
            if candidate_meta and (
                _authority(url) >= _authority(existing.canonical_source_url)
                or not existing_meta.get("source")
                or existing_meta.get("source") == "search_result"
            ):
                existing_meta.update(candidate_meta)
            existing.decision_metadata = existing_meta

            # Cross-posted events may be tagged for different personas or with
            # extra keywords; merging keeps one row while preserving reach.
            merged_tags = list(existing.tags or [])
            for tag in candidate.get("tags") or []:
                if tag not in merged_tags:
                    merged_tags.append(tag)
            existing.tags = merged_tags

            merged_personas = list(existing.domain_personas or [])
            for persona_id in candidate.get("domain_personas") or []:
                if persona_id not in merged_personas:
                    merged_personas.append(persona_id)
            existing.domain_personas = merged_personas
            merged += 1
            continue

        db.add(
            Opportunity(
                title=title[:250],
                category=str(candidate.get("category") or "general_event")[:50],
                canonical_source_url=url,
                host_organization=(candidate.get("host_organization") or None),
                deadline=deadline,
                city=(candidate.get("city") or None),
                event_date=(candidate.get("event_date") or deadline.date()),
                description=str(candidate.get("description") or title)[:8000],
                tags=list(candidate.get("tags") or []),
                domain_personas=list(candidate.get("domain_personas") or []),
                location_type=str(candidate.get("location_type") or "virtual"),
                reward_pool=candidate.get("reward_pool"),
                decision_metadata=candidate.get("decision_metadata") or {},
                embedding=embedding,
                sha256_hash=fingerprint,
            )
        )
        inserted += 1

    await db.flush()
    return {"inserted": inserted, "merged": merged, "skipped": skipped}


class OpportunityScout:
    def collect_candidates(self) -> List[Dict[str, Any]]:
        return collect_candidates()

    async def upsert(self, db: AsyncSession, candidates: List[Dict[str, Any]]):
        return await upsert_candidates(db, candidates)


opportunity_scout = OpportunityScout()
