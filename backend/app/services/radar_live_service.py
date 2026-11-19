"""Intent + recency Radar pipeline.

This module turns a project dossier into three narrow search queries, filters
provider results before they ever reach PostgreSQL, batch-reranks the survivors
with Gemini, and returns only live, openable sources. Discovery links that were
only meant for manual verification are never inserted into the Radar feed.
"""

from __future__ import annotations

import hashlib
import re
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.dossier import ProjectDossier
from app.models.opportunity import Opportunity
from app.schemas.signals import MarketSignal
from app.services.external_intelligence import external_intelligence
from app.services.gemini_client import gemini_service
from app.services.opportunity_discovery import deduplicate_candidates, discover_opportunities
from app.services.radar_engine import PERSONA_LABELS

RADAR_INTENTS: tuple[str, ...] = ("hackathons", "news", "builders")

_GENERIC_PATH_SEGMENTS = {
    "",
    "browse",
    "discover",
    "event",
    "events",
    "explore",
    "hackathon",
    "hackathons",
    "home",
    "index",
    "latest",
    "r",
    "search",
    "topic",
    "u",
    "user",
}

_VERIFICATION_MARKERS = (
    "verification link",
    "not a scraped post",
    "open the search results to confirm",
)

_DEADLINE_HINT = re.compile(
    r"(?:deadline|closes?|apply by|registration ends?|last date|submissions? close)",
    re.IGNORECASE,
)
_ISO_DATE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")

_REWARD_PATTERN = re.compile(
    r"(?:US)?\$\s?[\d,.]+(?:\s?(?:k|m|million|stipend))?", re.IGNORECASE
)


@dataclass
class IntentScanResult:
    intent: str
    query: str
    raw_count: int = 0
    gated_count: int = 0
    accepted_count: int = 0
    items: List[Dict[str, Any]] = field(default_factory=list)
    signals: List[MarketSignal] = field(default_factory=list)
    note: Optional[str] = None


def _parse_date(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        try:
            parsed = datetime.strptime(raw[:10], "%Y-%m-%d")
        except ValueError:
            return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def _explicit_deadline(text: str) -> Optional[datetime]:
    """Read a deadline only when the snippet says so and gives an ISO date."""

    if not _DEADLINE_HINT.search(text or ""):
        return None
    match = _ISO_DATE.search(text or "")
    if not match:
        return None
    parsed = _parse_date(match.group(1))
    if parsed and parsed.time() == datetime.min.time():
        parsed = parsed.replace(hour=23, minute=59)
    return parsed if parsed and parsed > datetime.now(timezone.utc) else None


def _host(url: str) -> str:
    try:
        return (urllib.parse.urlsplit(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def is_actionable_url(url: str) -> bool:
    """Reject root profiles and generic listing/search pages before persistence."""

    try:
        parts = urllib.parse.urlsplit((url or "").strip())
    except ValueError:
        return False
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return False

    host = (parts.hostname or "").lower().removeprefix("www.")
    path = (parts.path or "").rstrip("/")
    segments = [segment for segment in path.split("/") if segment]
    lowered_path = path.lower()

    if any(marker in host for marker in ("google.", "bing.", "yahoo.", "duckduckgo.")):
        return False
    if "localhost" in host or re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", host):
        return False

    if host in {"x.com", "twitter.com"}:
        return "/status/" in lowered_path
    if "reddit.com" in host:
        return "/comments/" in lowered_path
    if "news.ycombinator.com" in host:
        return "/item" in lowered_path or "id=" in lowered_path
    if "indiehackers.com" in host:
        return len(segments) >= 2 and segments[0].lower() not in _GENERIC_PATH_SEGMENTS

    event_hosts = tuple(settings.RADAR_HACKATHON_DOMAINS)
    if host.endswith(event_hosts):
        if not segments:
            return False
        if all(segment.lower() in _GENERIC_PATH_SEGMENTS for segment in segments):
            return False
        return len(segments) >= 2 or len(segments[0]) >= 12

    # Any other grounded page must have a real article/post path.
    if not segments:
        return False
    return segments[0].lower() not in _GENERIC_PATH_SEGMENTS or len(segments) >= 3


def _is_verification_placeholder(title: str, summary: str) -> bool:
    blob = f"{title} {summary}".lower()
    return any(marker in blob for marker in _VERIFICATION_MARKERS)


def _normalise_raw_item(
    raw: Dict[str, Any],
    *,
    intent: str,
    query: str,
) -> Optional[Dict[str, Any]]:
    url = str(raw.get("url") or "").strip()
    title = str(raw.get("title") or "").strip()
    summary = str(
        raw.get("content") or raw.get("summary") or raw.get("snippet") or raw.get("text") or ""
    ).strip()
    if not url or not title or not is_actionable_url(url):
        return None
    if _is_verification_placeholder(title, summary):
        return None

    published = _parse_date(raw.get("published_date") or raw.get("publishedDate"))
    deadline = _explicit_deadline(summary) or _parse_date(raw.get("deadline"))
    language = str(raw.get("language") or raw.get("lang") or "").strip().lower()
    item_id = hashlib.sha1(url.encode("utf-8")).hexdigest()[:14]

    return {
        "id": item_id,
        "intent": intent,
        "title": title[:250],
        "summary": summary[:1600] or title[:250],
        "url": url,
        "source": _source_for_url(intent, url),
        "published_at": published,
        "deadline": deadline,
        "deadline_explicit": deadline is not None,
        "language": language,
        "generated_query": query,
        "keywords": [],
        "relevance_score_100": 0,
        "rerank_reason": "",
    }


def _source_for_url(intent: str, url: str) -> str:
    if intent == "news":
        return "news"
    host = _host(url)
    if "reddit.com" in host:
        return "reddit"
    if host in {"x.com", "twitter.com"}:
        return "x"
    if "news.ycombinator.com" in host:
        return "hackernews"
    if "indiehackers.com" in host:
        return "indiehackers"
    return "builder" if intent == "builders" else "news"


def _to_market_signal(item: Dict[str, Any], keywords: Sequence[str]) -> MarketSignal:
    source = str(item.get("source") or "news")
    intent = str(item.get("intent") or "news")
    return MarketSignal(
        id=f"radar-{item['id']}",
        source=source,  # type: ignore[arg-type]
        signal_type="builder" if intent == "builders" else "news",  # type: ignore[arg-type]
        title=str(item.get("title") or "")[:250],
        summary=str(item.get("summary") or "")[:1600],
        url=str(item.get("url") or ""),
        published_at=item.get("published_at"),
        relevance_score=round(min(1.0, max(0.0, item.get("relevance_score_100", 0) / 100)), 2),
        keywords=list(keywords[:5]),
        is_live=True,
        radar_intent=intent,
    )


def _infer_category(title: str, summary: str) -> str:
    blob = f"{title} {summary}".lower()
    if any(word in blob for word in ("hackathon", "buildathon", "build sprint", "hack")):
        return "hackathon"
    if any(word in blob for word in ("grant", "funding", "prize")):
        return "grant"
    if any(word in blob for word in ("fellowship", "residency")):
        return "fellowship"
    return "general_event"


def _to_opportunity_candidate(
    item: Dict[str, Any],
    *,
    persona: str,
    tags: Sequence[str],
    scanned_at: datetime,
) -> Optional[Dict[str, Any]]:
    """Only explicit deadlines become opportunity rows; nothing is inferred."""

    deadline = item.get("deadline")
    if not isinstance(deadline, datetime) or deadline <= scanned_at:
        return None

    summary = str(item.get("summary") or "")
    reward_match = _REWARD_PATTERN.search(summary)
    url = str(item.get("url") or "")
    source_host = _host(url)
    return {
        "title": str(item.get("title") or "")[:250],
        "category": _infer_category(str(item.get("title") or ""), summary),
        "canonical_source_url": url,
        "host_organization": source_host or None,
        "deadline": deadline,
        "description": summary[:4000] or str(item.get("title") or "Live Radar result"),
        "tags": list(tags[:6]),
        "domain_personas": [persona],
        "location_type": "virtual",
        "reward_pool": reward_match.group(0) if reward_match else None,
        "decision_metadata": {
            "source": "search_result",
            "source_label": source_host or "Web search",
            "source_kind": "search_result",
            "verification": "verify_on_official_page",
            "is_official": False,
            "is_live": True,
            "deadline_inferred": False,
            "deadline_basis": "explicit_deadline",
            "radar_intent": item.get("intent"),
            "generated_query": item.get("generated_query"),
            "relevance_score_100": item.get("relevance_score_100", 0),
            "rerank_reason": item.get("rerank_reason", ""),
            "language": item.get("language"),
            "published_at": item.get("published_at").isoformat()
            if item.get("published_at")
            else None,
            "scanned_at": scanned_at.isoformat(),
        },
    }


def build_project_context(
    dossier: Optional[ProjectDossier],
    raw_idea: Optional[str],
    persona: str,
) -> Dict[str, Any]:
    """Collect only factual dossier fields for query planning and reranking."""

    idea = (raw_idea or "").strip()
    if dossier is not None:
        problem = (dossier.problem_statement or idea or dossier.tagline or "").strip()
        title = (dossier.title or "").strip()
        tagline = (dossier.tagline or "").strip()
        tech_stack = [str(item) for item in (dossier.tech_stack or []) if str(item).strip()]
        metrics = [
            f"{entry.get('label', '')}: {entry.get('value', '')}"
            for entry in (dossier.key_metrics or [])
            if isinstance(entry, dict) and entry.get("label")
        ]
    else:
        problem = idea
        title = idea.splitlines()[0][:80] if idea else ""
        tagline = ""
        tech_stack = []
        metrics = []

    summary_parts = [part for part in (title, tagline, problem, ", ".join(tech_stack[:6]), "; ".join(metrics[:3])) if part]
    return {
        "persona": persona,
        "persona_label": PERSONA_LABELS.get(persona, persona.replace("_", " ").title()),
        "title": title[:200],
        "tagline": tagline[:300],
        "problem_statement": problem[:4000],
        "raw_idea": idea[:4000],
        "tech_stack": tech_stack[:8],
        "key_metrics": metrics[:4],
        "solution_type": tagline or (dossier.stage if dossier is not None else "") or "",
        "summary": " | ".join(summary_parts)[:4500],
    }


async def collect_intent_candidates(
    *,
    context: Dict[str, Any],
    persona: str,
    intent: str,
    query: str,
    language: str,
    max_age_hours: int,
    keywords: Sequence[str],
) -> IntentScanResult:
    """Search, gatekeep, and rerank one Radar intent."""

    result = IntentScanResult(intent=intent, query=query)
    try:
        raw_results = await external_intelligence.search_for_intent(
            query,
            intent=intent,
            max_age_hours=max_age_hours,
        )
    except Exception as exc:  # provider/network failure must not break other tabs
        logger_note = f"Search provider unavailable: {type(exc).__name__}"
        result.note = logger_note
        return result

    result.raw_count = len(raw_results)
    seen: set[str] = set()
    gated: List[Dict[str, Any]] = []
    for raw in raw_results:
        if not isinstance(raw, dict):
            continue
        item = _normalise_raw_item(raw, intent=intent, query=query)
        if item is None or item["url"].rstrip("/").lower() in seen:
            continue
        seen.add(item["url"].rstrip("/").lower())
        gated.append(item)

    result.gated_count = len(gated)
    if not gated:
        return result

    accepted = await gemini_service.rerank_radar_results(
        gated,
        str(context.get("summary") or ""),
        intent,
        search_query=query,
        language=language,
    )
    result.items = accepted
    result.accepted_count = len(accepted)
    # Hackathons/grants surface as opportunity cards (only when they carry an
    # explicit deadline). Without one there is no actionable Radar card, so we
    # do not repurpose them as generic "news" signals.
    if intent in {"news", "builders"}:
        result.signals = [_to_market_signal(item, keywords) for item in accepted]
    return result


async def scan_live(
    *,
    db: AsyncSession,
    dossier: Optional[ProjectDossier],
    raw_idea: Optional[str],
    persona: str,
    intents: Sequence[str],
    language: str,
    max_age_hours: int,
) -> Dict[str, Any]:
    """Run the full on-demand scan and return a refreshed briefing + signals."""

    started = datetime.now(timezone.utc)
    selected = [intent for intent in RADAR_INTENTS if intent in set(intents)] or list(RADAR_INTENTS)
    context = build_project_context(dossier, raw_idea, persona)
    queries = await gemini_service.generate_radar_queries(context, language)
    keywords = list(context.get("tech_stack") or [])

    # Retrieval-first path: platform adapters turn the idea into real,
    # source-linked records before any ranking or copy is generated.
    discovery = await discover_opportunities(
        raw_idea=str(context.get("raw_idea") or context.get("summary") or ""),
        persona=persona,
    )

    results: List[IntentScanResult] = []
    all_signals: List[MarketSignal] = []
    candidates: List[Dict[str, Any]] = list(discovery.candidates)

    for intent in selected:
        scan_result = await collect_intent_candidates(
            context=context,
            persona=persona,
            intent=intent,
            query=queries[intent],
            language=language,
            max_age_hours=max_age_hours,
            keywords=keywords,
        )
        results.append(scan_result)
        all_signals.extend(scan_result.signals)
        for item in scan_result.items:
            candidate = _to_opportunity_candidate(
                item,
                persona=persona,
                tags=keywords or [persona],
                scanned_at=started,
            )
            if candidate:
                candidates.append(candidate)

    candidates = deduplicate_candidates(candidates)

    upsert_result: Dict[str, int] = {"inserted": 0, "merged": 0, "skipped": 0}
    if candidates:
        # Imported lazily so the Celery collector can reuse this module without
        # creating a circular import at startup.
        from app.services.opportunity_scout import upsert_candidates

        upsert_result = await upsert_candidates(db, candidates)

    opportunity_rows = list(
        (
            await db.execute(
                select(Opportunity).order_by(Opportunity.deadline.asc())
            )
        ).scalars().all()
    )
    from app.services.radar_engine import build_briefing

    briefing = build_briefing(opportunity_rows, persona, dossier=dossier)

    direct_raw = sum(source.raw_count for source in discovery.sources)
    direct_accepted = len(discovery.candidates)
    total_raw = direct_raw + sum(item.raw_count for item in results)
    total_accepted = direct_accepted + sum(item.accepted_count for item in results)
    status = "ok" if total_raw or direct_accepted else "empty"
    return {
        "status": status,
        "persona": persona,
        "language": language,
        "max_age_hours": max_age_hours,
        "queries": [
            {
                "intent": "opportunities",
                "query": discovery.query,
                "raw_results": direct_raw,
                "actionable_after_gatekeeper": direct_raw,
                "accepted": direct_accepted,
                "note": "Direct platform adapters: Devpost, MLH, Unstop, Luma, Grants.gov, Commudle discovery, Hackalendar.",
            }
        ] + [
            {
                "intent": item.intent,
                "query": item.query,
                "raw_results": item.raw_count,
                "actionable_after_gatekeeper": item.gated_count,
                "accepted": item.accepted_count,
                "note": item.note,
            }
            for item in results
        ],
        "sources": discovery.source_payload(),
        "stats": {
            "raw_results": total_raw,
            "actionable_after_gatekeeper": direct_raw + sum(item.gated_count for item in results),
            "accepted": total_accepted,
            "rejected": max(0, total_raw - total_accepted),
            "opportunities_inserted": upsert_result["inserted"],
            "opportunities_merged": upsert_result["merged"],
            "duration_ms": int(
                (datetime.now(timezone.utc) - started).total_seconds() * 1000
            ),
        },
        "briefing": briefing,
        "signals": all_signals,
    }
