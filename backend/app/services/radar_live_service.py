"""Intent + recency Radar pipeline.

This module turns a project dossier into three narrow search queries, filters
provider results before they ever reach PostgreSQL, batch-reranks the survivors
with Gemini, and returns only live, openable sources. Discovery links that were
only meant for manual verification are never inserted into the Radar feed.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import urllib.parse
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.dossier import ProjectDossier
from app.models.opportunity import Opportunity
from app.schemas.signals import MarketSignal
from app.services.concept_normalizer import build_concept_profile
from app.services.external_intelligence import external_intelligence
from app.services.gemini_client import gemini_service
from app.services.opportunity_discovery import deduplicate_candidates, discover_opportunities
from app.services.radar_engine import PERSONA_LABELS
from app.services.radar_intel import (
    explain_candidates,
    filter_market_signals,
    search_concept_intel,
)

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
    r"(?:deadline|closes?|closing|apply by|registration ends?|last date|"
    r"submissions? close|applications? close|register by|entries close)",
    re.IGNORECASE,
)
_ISO_DATE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
_MONTH_DATE = re.compile(
    r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|"
    r"dec(?:ember)?)\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+20\d{2}\b",
    re.IGNORECASE,
)
_NUMERIC_DATE = re.compile(r"\b\d{1,2}/\d{1,2}/20\d{2}\b")
_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

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


def _parse_natural_date(value: str) -> Optional[datetime]:
    """Parse the date formats real event snippets actually use."""

    raw = value.strip().rstrip(".,")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        parsed = None
    if parsed is None:
        month_match = re.match(
            r"([A-Za-z]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d{2})", raw
        )
        if month_match:
            month = _MONTHS.get(month_match.group(1).lower().rstrip("."))
            if month:
                try:
                    parsed = datetime(int(month_match.group(3)), month, int(month_match.group(2)))
                except ValueError:
                    parsed = None
        if parsed is None and re.fullmatch(r"\d{1,2}/\d{1,2}/20\d{2}", raw):
            month, day, year = (int(part) for part in raw.split("/"))
            try:
                parsed = datetime(year, month, day)
            except ValueError:
                parsed = None
    if parsed is None:
        return None
    parsed = parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    if parsed.time() == datetime.min.time():
        parsed = parsed.replace(hour=23, minute=59)
    return parsed


def _explicit_deadline(text: str) -> Optional[datetime]:
    """Read a deadline only when the snippet says so AND gives a real date.

    Deadlines appear as ``2026-12-01``, ``December 1, 2026``, ``1 Dec 2026``
    or ``12/01/2026`` in live search snippets. Accepting all of them (with a
    deadline hint next to the date) is what lets real hackathons and grants
    survive into the Radar feed without inferring anything.
    """

    content = text or ""
    hints = list(_DEADLINE_HINT.finditer(content))
    if not hints:
        return None
    dated: List[tuple[int, datetime]] = []
    for pattern in (_ISO_DATE, _MONTH_DATE, _NUMERIC_DATE):
        for match in pattern.finditer(content):
            parsed = _parse_natural_date(match.group(0))
            if parsed and parsed > datetime.now(timezone.utc):
                dated.append((match.start(), parsed))
    for hint in hints:
        for position, parsed in dated:
            if abs(position - hint.start()) <= 200:
                return parsed
    return None


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
    event_date = item.get("event_date")
    return {
        "title": str(item.get("title") or "")[:250],
        "category": str(item.get("category") or "").strip()
        or _infer_category(str(item.get("title") or ""), summary),
        "canonical_source_url": url,
        "host_organization": item.get("host_organization") or source_host or None,
        "deadline": deadline,
        "event_date": event_date.date() if isinstance(event_date, datetime) else event_date,
        "description": summary[:4000] or str(item.get("title") or "Live Radar result"),
        "tags": list(tags[:6]),
        "domain_personas": [persona],
        "location_type": "virtual",
        "reward_pool": item.get("reward_pool") or (reward_match.group(0) if reward_match else None),
        "decision_metadata": {
            "source": item.get("source") or "search_result",
            "source_label": item.get("source_label") or source_host or "Web search",
            "source_kind": item.get("source_kind") or "search_result",
            "verification": item.get("verification") or "verify_on_official_page",
            "is_official": bool(item.get("is_official", False)),
            "is_live": True,
            "deadline_inferred": False,
            "deadline_basis": item.get("date_basis") or "explicit_deadline",
            "radar_intent": item.get("intent") or item.get("bucket"),
            "generated_query": item.get("generated_query"),
            "relevance_score_100": item.get("relevance_score_100", 0),
            "match_score": round(min(1.0, item.get("relevance_score_100", 0) / 100), 2),
            "matched_terms": list(item.get("matched_terms") or []),
            "why_this_fits": item.get("why_this_fits") or "",
            "rerank_reason": item.get("rerank_reason") or item.get("why_this_fits") or "",
            "language": item.get("language"),
            "published_at": item.get("published_at").isoformat()
            if isinstance(item.get("published_at"), datetime)
            else item.get("published_at"),
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

    # Stage 2: messy idea -> structured, keyword-dense concept profile.
    profile = await build_concept_profile(context, language)
    queries = await gemini_service.generate_radar_queries(context, language)
    keywords = list(
        dict.fromkeys(
            [
                *(str(item) for item in (profile.get("core_entities") or [])),
                *(str(item) for item in (context.get("tech_stack") or [])),
            ]
        )
    )[:8]

    # Stage 3: run direct platform adapters, the 4-bucket Tavily search, and the
    # legacy intent scans together. A failure in one path cannot block the rest.
    async def legacy_scan(intent: str) -> IntentScanResult:
        return await collect_intent_candidates(
            context=context,
            persona=persona,
            intent=intent,
            query=queries[intent],
            language=language,
            max_age_hours=max_age_hours,
            keywords=keywords,
        )

    outcomes = await asyncio.gather(
        discover_opportunities(
            raw_idea=str(context.get("raw_idea") or context.get("summary") or ""),
            persona=persona,
        ),
        search_concept_intel(profile, language=language),
        *(legacy_scan(intent) for intent in selected),
        return_exceptions=True,
    )

    from types import SimpleNamespace

    discovery = outcomes[0] if not isinstance(outcomes[0], Exception) else SimpleNamespace(
        candidates=[], sources=[], query="", source_payload=lambda: []
    )
    intel = outcomes[1] if not isinstance(outcomes[1], Exception) else None
    results = [item for item in outcomes[2:] if isinstance(item, IntentScanResult)]

    all_signals: List[MarketSignal] = []
    candidates: List[Dict[str, Any]] = list(discovery.candidates)

    # Concept-normalized intel: actionable buckets become source-backed cards
    # only when a deadline or dated event was explicitly stated in the result.
    if intel is not None:
        for item in intel.items:
            bucket = str(item.get("bucket") or "")
            if bucket in {"news", "trends"}:
                all_signals.append(
                    MarketSignal(
                        id=f"radar-intel-{item['id']}",
                        source="news",
                        signal_type="trend" if bucket == "trends" else "news",  # type: ignore[arg-type]
                        title=str(item.get("title") or "")[:250],
                        summary=(
                            f"{item.get('snippet','')[:1200]} "
                            f"Why it fits: {item.get('why_this_fits','')[:240]}"
                        ).strip(),
                        url=str(item.get("url") or ""),
                        published_at=item.get("published_at"),
                        relevance_score=round(
                            min(1.0, item.get("relevance_score_100", 0) / 100), 2
                        ),
                        keywords=list(item.get("matched_terms") or keywords[:5])[:5],
                        is_live=True,
                        radar_intent="news",
                    )
                )
                continue
            if bucket not in {"events", "opportunities"} or not item.get("deadline"):
                continue
            blob = f"{item.get('title','')} {item.get('snippet','')}".lower()
            if bucket == "opportunities":
                category = "grant" if any(
                    word in blob
                    for word in ("grant", "funding", "fellowship", "accelerator", "stipend")
                ) else "general_event"
            elif any(word in blob for word in ("hackathon", "buildathon", "build sprint", "hack")):
                category = "hackathon"
            else:
                category = "general_event"
            candidate = _to_opportunity_candidate(
                {
                    **item,
                    "summary": item.get("snippet") or "",
                    "category": category,
                    "source": "tavily_search",
                    "source_label": f"Tavily · {bucket}",
                    "source_kind": "search_result",
                    "verification": "verify_on_official_page",
                },
                persona=persona,
                tags=keywords or [persona],
                scanned_at=started,
            )
            if candidate:
                candidates.append(candidate)

    # Legacy intent scans also emit news/trend signals. They must satisfy the
    # same concept gate and carry a Why it fits line before reaching the UI.
    legacy_signals = [
        signal for scan_result in results for signal in scan_result.signals
    ]
    all_signals.extend(filter_market_signals(legacy_signals, profile))

    for scan_result in results:
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
    # Stage 4: tie every surviving card back to the user's idea in one sentence
    # and discard listings that do not genuinely connect to the idea.
    explained = await explain_candidates(candidates, profile, language=language)
    candidates = explained.candidates

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
    direct_accepted = sum(
        1
        for candidate in candidates
        if str((candidate.get("decision_metadata") or {}).get("source_kind") or "")
        == "public_api"
    )
    intel_raw = intel.raw_count if intel is not None else 0
    intel_gated = intel.gated_count if intel is not None else 0
    intel_accepted = intel.accepted_count if intel is not None else 0
    total_raw = direct_raw + intel_raw + sum(item.raw_count for item in results)
    total_accepted = len(candidates)
    status = "ok" if total_raw or total_accepted else "empty"

    query_plans: List[Dict[str, Any]] = [
        {
            "intent": "opportunities",
            "query": discovery.query,
            "raw_results": direct_raw,
            "actionable_after_gatekeeper": len(discovery.candidates),
            "accepted": direct_accepted,
            "note": (
                "Direct platform adapters: Devpost, MLH, Unstop, Luma, Grants.gov, "
                "Commudle discovery, Hackalendar. "
                + (explained.note or "")
            ).strip(),
        }
    ]
    if intel is not None:
        query_plans.extend(intel.plans)
    query_plans.extend(
        {
            "intent": item.intent,
            "query": item.query,
            "raw_results": item.raw_count,
            "actionable_after_gatekeeper": item.gated_count,
            "accepted": item.accepted_count,
            "note": item.note,
        }
        for item in results
    )

    sources = list(discovery.source_payload())
    if intel is not None:
        sources.extend(intel.sources)

    return {
        "status": status,
        "persona": persona,
        "language": language,
        "max_age_hours": max_age_hours,
        "concept_profile": profile,
        "radar_queries": profile.get("radar_queries") or {},
        "queries": query_plans,
        "sources": sources,
        "stats": {
            "raw_results": total_raw,
            "actionable_after_gatekeeper": direct_raw + intel_gated + sum(item.gated_count for item in results),
            "accepted": total_accepted,
            "rejected": max(0, total_raw - total_accepted),
            "opportunities_inserted": upsert_result["inserted"],
            "opportunities_merged": upsert_result["merged"],
            "relevance_filtered": explained.rejected_count,
            "llm_verified": (
                (intel.llm_verified_count if intel is not None else 0)
                + explained.llm_verified_count
            ),
            "duration_ms": int(
                (datetime.now(timezone.utc) - started).total_seconds() * 1000
            ),
        },
        "briefing": briefing,
        "signals": all_signals,
    }
