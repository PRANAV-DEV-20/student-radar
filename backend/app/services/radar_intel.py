"""Concept-normalized Tavily intelligence for the Radar section.

Four searches run in parallel, each with hard API constraints:

* Trends   - advanced depth, 180-day window
* News     - Tavily's dedicated news topic, 30-day window
* Events   - locked to real hackathon / event portals, 60-day window
* Grants   - locked to grant / accelerator portals, 60-day window

Every provider hit passes two gates before it can reach the UI:

1. Tavily's own relevance score must clear the bucket gate (0.60 for open-web
   results, 0.30 for domain-locked event/grant portals).
2. A fast LLM verifies that the result directly relates to the user's core
   entities and writes a one-sentence ``why_this_fits`` justification.

Dates are only accepted when they are explicitly present in the retrieved
text. Nothing here invents an event, deadline, reward, or URL.
"""

from __future__ import annotations

import asyncio
import hashlib
import html
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

import httpx

from app.core.config import settings
from app.services.groq_client import groq_client
from app.services.concept_normalizer import RADAR_QUERY_KEYS

logger = logging.getLogger(__name__)

_TAVILY_URL = "https://api.tavily.com/search"
_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_MONTH_NAMES = {value: name for name, value in _MONTHS.items() if len(name) > 3}
_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}")
_FOCUS_STOPWORDS = {
    "about", "accelerator", "adoption", "agency", "analysis", "announcement",
    "application", "apply", "buildathon", "challenge", "competitor", "conference",
    "deadline", "development", "event", "fellowship", "funding", "global", "grant",
    "growth", "hackathon", "india", "industry", "innovation", "launch", "market",
    "new", "news", "opportunity", "outlook", "platform", "program", "project",
    "recent", "report", "research", "review", "scheme", "sector", "startup",
    "student", "students", "submission", "summit", "technology", "through",
    "trend", "trends", "upcoming", "using", "world",
    # Narrative words from problem statements are not relevance anchors. They
    # previously let generic medical "disease detection" grants through.
    "early", "lack", "lacks", "lacking", "low", "cheap", "works", "working",
    "need", "needs", "want", "wants", "detector", "farms", "phones",
}
# Broad words only establish the general domain. They cannot by themselves
# justify a card: "agriculture" or "crop" appears in thousands of listings.
_GENERIC_FOCUS = {
    "ai", "agri", "agriculture", "agricultural", "agritech", "artificial", "computer",
    "computing", "detection", "device", "devices", "deployment", "edge", "farmer",
    "farmers", "harvest", "intelligence", "learning", "machine", "mobile", "smart",
    "solution", "solutions", "system", "systems", "vision",
}
_CONTEXT_FOCUS = {
    "agri", "agriculture", "agricultural", "agritech", "blight", "crop", "crops",
    "edge", "farmer", "farmers", "leaf", "mobile", "offline", "pytorch",
    "smallholder", "vision",
}
_STRONG_SPECIFIC_FOCUS = {
    "blight", "identification", "leaf", "offline", "pytorch", "smallholder",
}
_VENUE_HINT = re.compile(
    r"\b(?:hackathon|buildathon|innovation|challenge|summit|accelerator|"
    r"fellowship|grant|funding|startup)\b",
    re.IGNORECASE,
)
_VENUE_EXCLUDE = re.compile(
    r"\b(?:ctf|capture the flag|cybersecurity)\b",
    re.IGNORECASE,
)
_HEDGE_REASON = re.compile(
    r"\b(?:could|might|may|potentially|possibly|though|however|broadly|generally)\b",
    re.IGNORECASE,
)
_NEGATIVE_REASON = re.compile(
    r"\b(?:unrelated|does not|doesn't|not (?:specific|directly|really|focused|"
    r"relevant|aimed|for)|no (?:specific|direct)|lacks?|without|generic|"
    r"only broadly|irrelevant)\b",
    re.IGNORECASE,
)
_DEADLINE_HINT = re.compile(
    r"(?:deadline|closes?|closing|apply by|registration ends?|last date|"
    r"submissions? close|applications? close|register by|entries close|"
    r"event date|starts?|begins?|submission period)",
    re.IGNORECASE,
)


@dataclass
class ConceptIntelResult:
    items: List[Dict[str, Any]] = field(default_factory=list)
    plans: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    raw_count: int = 0
    gated_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    llm_verified_count: int = 0
    note: Optional[str] = None


@dataclass
class CandidateExplanationResult:
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    accepted_count: int = 0
    rejected_count: int = 0
    llm_verified_count: int = 0
    note: Optional[str] = None


def _current_years() -> Tuple[int, int]:
    year = datetime.now(timezone.utc).year
    return year, year + 1


def _min_score(bucket: str) -> float:
    """Provider-side gate; domain-locked searches score on a lower scale."""

    if bucket in {"events", "opportunities"}:
        return settings.RADAR_TAVILY_DOMAIN_MIN_SCORE
    if bucket in {"trends", "news"}:
        return settings.RADAR_TAVILY_SIGNAL_MIN_SCORE
    return settings.RADAR_TAVILY_MIN_SCORE


def _event_query(query: str, year: int, next_year: int) -> str:
    """Ensure event searches always carry fresh-year intent."""

    has_year = str(year) in query or str(next_year) in query
    return query if has_year else f"{query.strip()} {year} {next_year}"


def _focus_phrases(profile: Dict[str, Any]) -> List[str]:
    """Must-have phrases from the normalized profile, not search filler."""

    values: List[str] = []
    for key in ("core_entities", "tech_stack"):
        values.extend(str(item).strip() for item in (profile.get(key) or []))
    values.extend(
        str(profile.get(key) or "").strip()
        for key in ("core_domain", "project_title", "target_audience")
    )
    phrases: List[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = " ".join(value.lower().split())
        if len(cleaned) < 4 or cleaned in seen:
            continue
        # A single broad tech-stack word like "Mobile" is not a must-have
        # phrase. Neither is a multiword phrase made only of generic words.
        words = re.findall(r"[a-z0-9+#.-]+", cleaned)
        if " " not in cleaned and cleaned not in _STRONG_SPECIFIC_FOCUS:
            continue
        specific_phrase = any(
            word not in _GENERIC_FOCUS and word not in _FOCUS_STOPWORDS
            for word in words
        )
        domain_phrase = len(words) >= 2 and any(
            word in _CONTEXT_FOCUS for word in words
        )
        if not (specific_phrase or domain_phrase):
            continue
        seen.add(cleaned)
        phrases.append(cleaned)
    return phrases[:10]


def _focus_tokens(profile: Dict[str, Any]) -> List[str]:
    """Concrete words that describe the user's idea, not narrative filler."""

    # Problem statements contain words like "lack", "early", and "disease".
    # Matching those alone produces confident-sounding false positives, so the
    # token set is built from the entities/domain/audience the planner extracted.
    text = " ".join(
        str(item)
        for item in (
            *(profile.get("core_entities") or []),
            *(profile.get("tech_stack") or []),
            profile.get("core_domain") or "",
            profile.get("target_audience") or "",
        )
    )
    seen: set[str] = set()
    tokens: List[str] = []
    for match in _TOKEN_RE.finditer(text.lower()):
        token = match.group(0).strip(".-")
        if (
            len(token) < 4
            or token in _FOCUS_STOPWORDS
            or token in seen
            or token.isdigit()
        ):
            continue
        seen.add(token)
        tokens.append(token)
    return tokens[:16]


def _matched_focus(text: str, focus_tokens: Sequence[str]) -> List[str]:
    haystack = f" {(text or '').lower()} "
    return [
        token
        for token in focus_tokens
        if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", haystack)
    ][:5]


def _matched_phrases(text: str, profile: Dict[str, Any]) -> List[str]:
    haystack = (text or "").lower()
    return [phrase for phrase in _focus_phrases(profile) if phrase in haystack][:5]


def _has_genuine_match(
    matched: Sequence[str],
    phrases: Sequence[str] = (),
    bucket: str = "",
) -> bool:
    """Require concrete concept overlap, not just a broad domain word."""

    specific = [token for token in matched if token not in _GENERIC_FOCUS]
    contextual = [token for token in matched if token in _CONTEXT_FOCUS]
    # Trend reports often describe the idea's field rather than the product;
    # two field anchors ("edge" + "agriculture") are meaningful there. News
    # needs a concrete idea token so generic AI round-ups cannot slip through.
    domain_level = bucket == "trends" and len(contextual) >= 2
    return (
        bool(phrases)
        or any(token in _STRONG_SPECIFIC_FOCUS for token in matched)
        or (len(specific) >= 2 and bool(contextual))
        or domain_level
    )


def _concrete_terms(
    phrases: Sequence[str],
    tokens: Sequence[str],
    bucket: str = "",
) -> List[str]:
    """Terms specific enough to appear in a Why this fits sentence."""

    generic = _GENERIC_FOCUS | _FOCUS_STOPWORDS
    signal_bucket = bucket == "trends"
    concrete: List[str] = []
    for phrase in phrases:
        words = re.findall(r"[a-z0-9+#.-]+", phrase.lower())
        specific = any(word not in generic for word in words)
        domain = signal_bucket and len(words) >= 2 and any(
            word in _CONTEXT_FOCUS for word in words
        )
        if specific or domain:
            concrete.append(phrase)
    for token in tokens:
        if token not in generic or (signal_bucket and token in _CONTEXT_FOCUS):
            concrete.append(token)
    return list(dict.fromkeys(concrete))


def _reason_is_grounded(
    reason: str,
    profile: Dict[str, Any],
    bucket: str = "",
) -> bool:
    """Reject polished but unrelated justifications before they reach the UI."""

    text = (reason or "").strip().lower()
    if not text or _NEGATIVE_REASON.search(text) or _HEDGE_REASON.search(text):
        return False
    return _has_genuine_match(
        _matched_focus(text, _focus_tokens(profile)),
        _matched_phrases(text, profile),
        bucket,
    )


def _venue_reason(text: str, profile: Dict[str, Any]) -> Optional[str]:
    """Explain a broad but usable event without inventing listing details."""

    lowered = (text or "").lower()
    hint = _VENUE_HINT.search(lowered)
    if not hint or _VENUE_EXCLUDE.search(lowered):
        return None
    matched = _matched_focus(lowered, _focus_tokens(profile))
    concept_context = any(token in _CONTEXT_FOCUS for token in matched)
    ai_event = bool(re.search(r"\b(?:ai|artificial intelligence)\b", lowered)) and any(
        word in lowered for word in ("hackathon", "buildathon", "innovation", "challenge")
    )
    if not (concept_context or ai_event):
        return None
    word = hint.group(0)
    if word in {"grant", "funding"}:
        venue = "funding program"
    elif word in {"accelerator", "fellowship"}:
        venue = "accelerator"
    elif word in {"hackathon", "buildathon"}:
        venue = "hackathon"
    elif word == "challenge":
        venue = "challenge"
    elif word == "summit":
        venue = "summit"
    else:
        venue = "innovation event"
    domain = str(profile.get("core_domain") or "concept").strip()
    audience = str(profile.get("target_audience") or "").strip()
    audience_text = f" for {audience}" if audience and audience.lower() not in domain.lower() else ""
    reason = f"This {venue} is a practical place to build or pitch your {domain} idea{audience_text}."
    return reason if _reason_is_grounded(reason, profile) else None


def _keyword_dense_query(
    query: str,
    bucket: str,
    profile: Dict[str, Any],
) -> str:
    """Keep planner queries specific even when the model returns 3 words."""

    base = " ".join((query or "").split())
    if len(base.split()) >= 5:
        return base[:220]
    anchors: List[str] = [str(profile.get("core_domain") or "")]
    anchors.extend(str(item) for item in (profile.get("core_entities") or [])[:3])
    extras: List[str] = []
    lowered = base.lower()
    for anchor in anchors:
        for word in anchor.split():
            word = word.strip(".,")
            if len(word) < 3 or word.lower() in lowered or word in extras:
                continue
            extras.append(word)
            if len(base.split()) + len(extras) >= 7:
                break
        if len(base.split()) + len(extras) >= 7:
            break
    if bucket == "news" and "launch" not in lowered:
        extras.extend(word for word in ("breakthrough", "launch") if word not in extras)
    return " ".join([base, *extras]).strip()[:220]


def _explicit_date_from_text(text: str) -> Optional[datetime]:
    """Read a future date only when a deadline/event hint appears beside it."""

    content = text or ""
    hints = list(_DEADLINE_HINT.finditer(content))
    if not hints:
        return None
    patterns = (
        re.compile(r"\b20\d{2}-\d{2}-\d{2}\b"),
        re.compile(
            r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
            r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|"
            r"dec(?:ember)?)\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+20\d{2}\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|"
            r"apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|"
            r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?,?\s+20\d{2}\b",
            re.IGNORECASE,
        ),
        re.compile(r"\b\d{1,2}/\d{1,2}/20\d{2}\b"),
    )
    dated: List[tuple[int, datetime]] = []
    for pattern in patterns:
        for match in pattern.finditer(content):
            raw = match.group(0).strip().rstrip(".,")
            parsed: Optional[datetime] = None
            if re.fullmatch(r"20\d{2}-\d{2}-\d{2}", raw):
                parsed = _parse_date(raw)
            elif re.fullmatch(r"\d{1,2}/\d{1,2}/20\d{2}", raw):
                month, day, year = (int(part) for part in raw.split("/"))
                try:
                    parsed = datetime(year, month, day, tzinfo=timezone.utc)
                except ValueError:
                    parsed = None
            else:
                month_match = re.match(
                    r"([A-Za-z]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d{2})", raw
                )
                day_match = re.match(
                    r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\.?,?\s+(20\d{2})", raw
                )
                if month_match:
                    month = _MONTHS.get(month_match.group(1).lower().rstrip("."))
                    if month:
                        try:
                            parsed = datetime(
                                int(month_match.group(3)),
                                month,
                                int(month_match.group(2)),
                                tzinfo=timezone.utc,
                            )
                        except ValueError:
                            parsed = None
                elif day_match:
                    month = _MONTHS.get(day_match.group(2).lower().rstrip("."))
                    if month:
                        try:
                            parsed = datetime(
                                int(day_match.group(3)),
                                month,
                                int(day_match.group(1)),
                                tzinfo=timezone.utc,
                            )
                        except ValueError:
                            parsed = None
            if parsed and parsed > datetime.now(timezone.utc):
                dated.append((match.start(), parsed))
    for hint in hints:
        for position, parsed in dated:
            if abs(position - hint.start()) <= 200:
                return parsed
    return None


def search_plans(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build the exact Tavily call for each of the four Radar buckets."""

    year, next_year = _current_years()
    queries = dict(profile.get("radar_queries") or {})
    fallback = profile.get("core_entities") or [profile.get("core_domain") or "student project"]
    entity_text = " ".join(str(item) for item in fallback[:5]) or "student innovation"
    domain = str(profile.get("core_domain") or "student innovation")

    def query_for(key: str, default: str) -> str:
        value = str(queries.get(key) or "").strip()
        base = value or default.format(domain=domain, entities=entity_text, year=year)
        return _keyword_dense_query(base, key, profile)

    limit = max(3, settings.RADAR_INTEL_MAX_RESULTS)
    return [
        {
            "bucket": "trends",
            "query": query_for(
                "trends", "{domain} {entities} market growth trends adoption {year}"
            ),
            "options": {
                "topic": "general",
                "search_depth": "advanced",
                "days": settings.RADAR_TREND_DAYS,
                "min_score": _min_score("trends"),
            },
        },
        {
            "bucket": "news",
            "query": query_for(
                "news", "{entities} breakthrough launch OR release OR funding"
            ),
            "options": {
                "topic": "news",
                "search_depth": "advanced",
                "days": settings.RADAR_NEWS_DAYS,
                "min_score": _min_score("news"),
            },
        },
        {
            "bucket": "events",
            "query": _event_query(
                query_for(
                    "events",
                    "{domain} {entities} hackathon OR summit OR buildathon {year}",
                ),
                year,
                next_year,
            ),
            "options": {
                "topic": "general",
                "search_depth": "advanced",
                "days": settings.RADAR_OPPORTUNITY_DAYS,
                "include_domains": list(settings.RADAR_EVENT_DOMAINS),
                "min_score": _min_score("events"),
            },
        },
        {
            "bucket": "opportunities",
            "query": query_for(
                "opportunities",
                "{domain} {entities} startup grant OR accelerator OR fellowship",
            ),
            "options": {
                "topic": "general",
                "search_depth": "advanced",
                "days": settings.RADAR_OPPORTUNITY_DAYS,
                "include_domains": list(settings.RADAR_OPPORTUNITY_DOMAINS),
                "min_score": _min_score("opportunities"),
            },
        },
    ]


async def _tavily_search(
    client: httpx.AsyncClient,
    query: str,
    options: Dict[str, Any],
    limit: int,
) -> List[Dict[str, Any]]:
    key = (settings.TAVILY_API_KEY or "").strip()
    if not key:
        return []
    options = dict(options)
    min_score = float(options.pop("min_score", settings.RADAR_TAVILY_MIN_SCORE))
    payload: Dict[str, Any] = {
        "api_key": key,
        "query": query,
        "max_results": limit,
        "score_threshold": min_score,
        "include_published_date": True,
        **options,
    }
    response = await client.post(_TAVILY_URL, json=payload)
    response.raise_for_status()
    return list((response.json() or {}).get("results") or [])


_SEARCH_MODIFIERS = {
    "ai", "artificial", "automated", "edge", "mobile", "offline", "real-time",
    "smart", "using", "with",
}


def _rss_query(plan: Dict[str, Any], profile: Dict[str, Any]) -> str:
    """Use compact concept phrases; long planner queries return nothing on RSS."""

    bucket = str(plan.get("bucket") or "")
    days = int(plan.get("options", {}).get("days") or settings.RADAR_TREND_DAYS)
    if bucket == "trends":
        return f"{plan['query']} when:{days}d"

    phrases: List[str] = []
    for phrase in _focus_phrases(profile):
        words = phrase.split()
        while words and words[0].lower() in _SEARCH_MODIFIERS:
            words.pop(0)
        cleaned = " ".join(words)
        if len(cleaned) >= 4 and cleaned not in phrases:
            phrases.append(cleaned)
    subject = phrases[:2] or [str(profile.get("core_domain") or "student project")]
    query = " OR ".join(f'"{item}"' for item in subject)
    return f"{query} AI when:{days}d"


async def _rss_search(
    client: httpx.AsyncClient,
    plan: Dict[str, Any],
    profile: Dict[str, Any],
    limit: int,
) -> List[Dict[str, Any]]:
    """Real public-news fallback when Tavily is rate-limited or unavailable.

    Google News RSS returns actual article links and titles. Scores are only a
    pass-through for the existing provider gate; dates and claims come from the
    feed, and every result still faces the strict concept verifier.
    """

    query = _rss_query(plan, profile)
    response = await client.get(
        "https://news.google.com/rss/search",
        params={"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"},
        headers={"User-Agent": "Mozilla/5.0 (compatible; StudentRadar/1.0)"},
    )
    response.raise_for_status()
    root = ET.fromstring(response.text)
    days = int(plan.get("options", {}).get("days") or settings.RADAR_TREND_DAYS)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    min_score = float(
        plan.get("options", {}).get("min_score", settings.RADAR_TAVILY_MIN_SCORE)
    )

    results: List[Dict[str, Any]] = []
    for node in root.findall(".//item")[:limit]:
        title = " ".join((node.findtext("title") or "").split())
        url = (node.findtext("link") or "").strip()
        if not title or not url.startswith(("http://", "https://")):
            continue
        description = html.unescape(
            re.sub(r"<[^>]+>", " ", node.findtext("description") or "")
        )
        snippet = " ".join(description.split())[:1600] or title
        published: Optional[datetime] = None
        raw_published = node.findtext("pubDate")
        if raw_published:
            try:
                parsed = parsedate_to_datetime(raw_published)
                published = parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
            except (TypeError, ValueError):
                published = None
        if published and published < cutoff:
            continue
        results.append(
            {
                "title": title,
                "url": url,
                "content": snippet,
                "published_date": published.isoformat() if published else "",
                "score": min_score,
                "provider": "google_news_rss",
            }
        )
    return results


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


def _date_grounded(iso_value: str, text: str) -> bool:
    """Only accept an LLM-extracted date that appears in the source text."""

    parsed = _parse_date(iso_value)
    if parsed is None:
        return False
    text = (text or "").lower()
    month_name = _MONTH_NAMES.get(parsed.month, "")
    candidates = {
        parsed.strftime("%Y-%m-%d"),
        parsed.strftime("%Y/%m/%d"),
        f"{parsed.day}/{parsed.month}/{parsed.year}",
        f"{parsed.month}/{parsed.day}/{parsed.year}",
        f"{month_name} {parsed.day}, {parsed.year}",
        f"{month_name} {parsed.day} {parsed.year}",
        f"{parsed.day} {month_name} {parsed.year}",
        f"{month_name} {parsed.day:02d}, {parsed.year}",
        f"{parsed.day:02d} {month_name} {parsed.year}",
        f"{parsed.year}-{parsed.month:02d}-{parsed.day:02d}",
    }
    for short in ("jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec"):
        name = _MONTHS[short]
        if name == parsed.month:
            candidates.add(f"{short} {parsed.day}, {parsed.year}")
            candidates.add(f"{short} {parsed.day} {parsed.year}")
            candidates.add(f"{short} {parsed.day:02d}, {parsed.year}")
            candidates.add(f"{parsed.day:02d} {short} {parsed.year}")
    return any(candidate.lower() in text for candidate in candidates)


def _future(value: Optional[datetime]) -> Optional[datetime]:
    if value is None or value <= datetime.now(timezone.utc):
        return None
    return value


def _item_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:14]


def _normalise_raw(
    raw: Dict[str, Any],
    *,
    bucket: str,
    query: str,
    min_score: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    url = str(raw.get("url") or "").strip()
    title = str(raw.get("title") or "").strip()
    snippet = " ".join(
        str(raw.get("content") or raw.get("summary") or raw.get("text") or "").split()
    ).strip()
    if not url.startswith(("http://", "https://")) or not title:
        return None
    try:
        score = float(raw.get("score") or 0.0)
    except (TypeError, ValueError):
        score = 0.0
    if score < (min_score if min_score is not None else _min_score(bucket)):
        return None

    return {
        "id": _item_id(url),
        "bucket": bucket,
        "provider": str(raw.get("provider") or "tavily"),
        "title": title[:250],
        "url": url,
        "snippet": snippet[:2400] or title[:250],
        "score": round(score, 3),
        "published_at": _parse_date(raw.get("published_date") or raw.get("publishedDate")),
        "generated_query": query,
        "matched_terms": [],
        "relevance_score_100": round(score * 100),
        "why_this_fits": "",
        "deadline": None,
        "event_date": None,
        "date_basis": None,
        "llm_verified": False,
    }


def _heuristic_terms(item: Dict[str, Any], core_entities: Sequence[str]) -> List[str]:
    haystack = f"{item.get('title','')} {item.get('snippet','')}".lower()
    return [
        str(entity)
        for entity in core_entities
        if str(entity).strip() and str(entity).lower() in haystack
    ][:5]


_VERIFY_PROMPT = """You are the relevance gatekeeper for a student opportunity radar.

The user's concept:
{concept}

Must-have core entities: {entities}

For EVERY search result below, decide whether it directly relates to the user's core problem. Return JSON only:
{{"results": [{{"id": "...", "relevant": true/false, "score": 0-100, "why_this_fits": "one sentence linking this result to the user's concept", "deadline": "YYYY-MM-DD or empty", "event_date": "YYYY-MM-DD or empty"}}]}}

RULES:
- Score 70+ for a direct concept match. Score 60-69 for a broad but actionable technology, agriculture, or startup context where this concept can realistically be built, pitched, or funded. Score below 60 only when the topic or audience makes the idea implausible.
- Write why_this_fits in ONE sentence naming the user's concrete concept entity (for example offline crop disease detection, leaf blight identification, smallholder farmers, PyTorch edge deployment). Broad words alone such as "AI", "agriculture", "crop", or "mobile" are NOT a fit. Do not hedge with "could", "might", or "could include".
- If the result only shares a broad domain word with no concrete concept link, mark relevant false. If it does not fit, still write one short sentence explaining why.
- Extract a date ONLY if the result text explicitly states a registration/submission deadline or an event date. Otherwise output an empty string. Never invent or guess a date.
- Include exactly one entry per id.

RESULTS:
{results}
"""


async def _verify_items(
    items: List[Dict[str, Any]],
    profile: Dict[str, Any],
    language: str,
) -> Tuple[List[Dict[str, Any]], int]:
    """Drop weak matches and attach one-sentence justifications."""

    if not items:
        return [], 0
    entities = [str(item) for item in (profile.get("core_entities") or [])][:8]
    cutoff = settings.RADAR_LLM_MIN_SCORE
    payload = [
        {
            "id": item["id"],
            "bucket": item["bucket"],
            "title": item["title"][:200],
            "snippet": item["snippet"][:900],
        }
        for item in items
    ]
    concept = " ".join(
        str(profile.get(key) or "")
        for key in ("project_title", "core_domain", "problem_statement", "target_audience")
    )[:1800]
    parsed = await groq_client.generate_json(
        _VERIFY_PROMPT.format(
            concept=concept,
            entities=", ".join(entities),
            results=str(payload)[:14000],
        ),
        system=(
            f"Answer in {language}. You are a strict relevance judge. "
            "Return JSON only. Do not invent dates, URLs, or facts."
        ),
        max_tokens=2400,
    )

    verdicts: Dict[str, Dict[str, Any]] = {}
    if parsed:
        rows = parsed.get("results") if isinstance(parsed, dict) else parsed
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict) and row.get("id") is not None:
                    verdicts[str(row["id"])] = row

    accepted: List[Dict[str, Any]] = []
    verified_count = 0
    focus = _focus_tokens(profile)
    for item in items:
        verdict = verdicts.get(item["id"])
        text = f"{item['title']} {item['snippet']}"
        matched = _matched_focus(text, focus)
        matched_phrases = _matched_phrases(text, profile)
        genuine = _has_genuine_match(matched, matched_phrases, item["bucket"])
        concrete = _concrete_terms(matched_phrases, matched, item["bucket"])
        if verdict is None:
            # Without a reasoning verdict, require a concrete concept overlap.
            # A high search score or a single generic word is not a fit.
            if not genuine or not concrete:
                continue
            score = min(88, 62 + 8 * len(concrete))
            reason = (
                f"Mentions {', '.join(concrete[:3])}, which connects "
                f"directly to your {profile.get('core_domain') or 'concept'} focus."
            )
            if not _reason_is_grounded(reason, profile, item["bucket"]):
                continue
            deadline_raw = event_raw = ""
        else:
            try:
                score = max(0, min(100, int(round(float(verdict.get("score", 0))))))
            except (TypeError, ValueError):
                score = 0
            if verdict.get("relevant") is False:
                score = min(score, cutoff - 1)
            reason = str(verdict.get("why_this_fits") or "").strip()[:300]
            deadline_raw = str(verdict.get("deadline") or "").strip()
            event_raw = str(verdict.get("event_date") or "").strip()
            verified_count += 1
            # A confident but generic sentence like "relates to disease" must
            # never become a Why this fits card. Rebuild it from concrete terms
            # when the underlying item really does match the concept.
            if not _reason_is_grounded(reason, profile, item["bucket"]):
                if not genuine or not concrete:
                    continue
                reason = (
                    f"Mentions {', '.join(concrete[:3])}, which connects "
                    f"directly to your {profile.get('core_domain') or 'concept'} focus."
                )
                if not _reason_is_grounded(reason, profile, item["bucket"]):
                    continue
                score = min(score, 69)

        if score < cutoff or not reason:
            continue

        enriched = dict(item)
        enriched["relevance_score_100"] = score
        enriched["why_this_fits"] = reason
        enriched["matched_terms"] = list(dict.fromkeys([*matched_phrases, *matched]))[:5]
        enriched["llm_verified"] = verdict is not None

        text = f"{item['title']} {item['snippet']}"
        deadline = _future(_parse_date(deadline_raw)) if _date_grounded(deadline_raw, text) else None
        event_date = _future(_parse_date(event_raw)) if _date_grounded(event_raw, text) else None
        if deadline:
            enriched["deadline"] = deadline
            enriched["date_basis"] = "registration_deadline"
        elif event_date:
            enriched["deadline"] = event_date
            enriched["event_date"] = event_date
            enriched["date_basis"] = "event_date"
        elif item["bucket"] in {"events", "opportunities"}:
            # The model sometimes omits a date that is plainly in the snippet.
            # Read it here, but only when a deadline/event cue sits next to it.
            detected = _explicit_date_from_text(text)
            if detected:
                enriched["deadline"] = detected
                enriched["date_basis"] = "registration_deadline"

        accepted.append(enriched)

    accepted.sort(key=lambda entry: entry["relevance_score_100"], reverse=True)
    return accepted, verified_count


_EXPLAIN_PROMPT = """You are the strict relevance gatekeeper for a student opportunity radar.

Concept: {concept}
Must-have entities: {entities}

For each item below, decide whether it offers a practical place to build, pitch, fund, or research the student's concept. Write ONE sentence linking a genuine match to the concept, or plainly state why it does not fit. Name a concrete concept entity in the reason; broad words such as "AI", "agriculture", "crop", or "mobile" alone are NOT a fit, and hedged reasons with "could" or "might" are not acceptable. List the matched core entities and score the fit 0-100. Score 70+ for a direct match; 60-69 for a broad but usable tech/agri/startup context; below 60 only when the idea is implausible there.

Return JSON only: {{"results": [{{"id": "0", "relevant": true, "why_this_fits": "one sentence", "matched_entities": ["..."], "score": 0}}]}}
Include one entry per id. Do not invent deadlines, rewards, or URLs.

ITEMS:
{items}
"""

async def explain_candidates(
    candidates: List[Dict[str, Any]],
    profile: Dict[str, Any],
    *,
    language: str = "en",
) -> CandidateExplanationResult:
    """Explain AND filter source-backed opportunity cards.

    Direct platform adapters return real but unexplained listings. A single
    batched Groq call ties each one back to the user's concept. Items that do
    not genuinely connect are discarded instead of being forced into the feed.
    If Groq is unavailable, only exact non-generic entity matches survive.
    """

    result = CandidateExplanationResult()
    if not candidates:
        return result

    entities = [str(item) for item in (profile.get("core_entities") or [])][:8]
    concept = " ".join(
        str(profile.get(key) or "")
        for key in ("project_title", "core_domain", "problem_statement", "target_audience")
    )[:1600]
    # Cards already justified by the grounded search stage keep their reason
    # when it passes the same strict check. Only unexplained cards need a new
    # model verdict, so a model outage cannot discard real source-backed cards.
    cutoff = settings.RADAR_LLM_MIN_SCORE
    targets: List[tuple[int, Dict[str, Any]]] = []
    for index, candidate in enumerate(candidates):
        metadata = candidate.get("decision_metadata") or {}
        prior_reason = str(metadata.get("why_this_fits") or "").strip()[:300]
        if not prior_reason or not _reason_is_grounded(prior_reason, profile):
            targets.append((index, candidate))
            continue
        try:
            prior_score = float(
                metadata.get("relevance_score_100")
                or float(metadata.get("match_score") or 0) * 100
            )
        except (TypeError, ValueError):
            prior_score = 0
        if prior_score < cutoff:
            targets.append((index, candidate))
            continue
        result.candidates.append(candidate)
        result.accepted_count += 1

    verdicts: Dict[str, Dict[str, Any]] = {}
    if groq_client.configured:
        payload = [
            {
                "id": str(index),
                "title": str(candidate.get("title") or "")[:200],
                "description": str(candidate.get("description") or "")[:600],
                "source": str((candidate.get("decision_metadata") or {}).get("source_label") or ""),
            }
            for index, candidate in targets
        ]
        parsed = await groq_client.generate_json(
            _EXPLAIN_PROMPT.format(
                concept=concept,
                entities=", ".join(entities),
                items=str(payload)[:16000],
            ),
            system=(
                f"Answer in {language}. You are a strict relevance judge. "
                "Return JSON only. Do not invent facts."
            ),
            max_tokens=2600,
        )
        if parsed:
            rows = parsed.get("results") if isinstance(parsed, dict) else parsed
            if isinstance(rows, list):
                for row in rows:
                    if isinstance(row, dict) and row.get("id") is not None:
                        verdicts[str(row["id"])] = row

    focus = _focus_tokens(profile)
    for index, candidate in targets:
        metadata = dict(candidate.get("decision_metadata") or {})
        verdict = verdicts.get(str(index))
        haystack = f"{candidate.get('title','')} {candidate.get('description','')}"
        matched = _matched_focus(haystack, focus)
        matched_phrases = _matched_phrases(haystack, profile)
        anchors = list(dict.fromkeys([*matched_phrases, *matched]))
        concrete = _concrete_terms(matched_phrases, matched)
        if verdict is None:
            # Without a reasoning verdict, require a concrete concept overlap,
            # or a real event/funding venue that can host the idea.
            reason = None
            if _has_genuine_match(matched, matched_phrases) and concrete:
                score = min(88, 62 + 8 * len(concrete))
                reason = (
                    f"This listing directly touches your "
                    f"{profile.get('core_domain') or 'concept'} focus on "
                    f"{', '.join(concrete[:3])}."
                )
                if not _reason_is_grounded(reason, profile):
                    reason = None
            if reason is None:
                reason = _venue_reason(haystack, profile)
                score = 65
            if not reason:
                result.rejected_count += 1
                continue
        else:
            result.llm_verified_count += 1
            try:
                score = max(0, min(100, int(round(float(verdict.get("score", 0))))))
            except (TypeError, ValueError):
                score = 0
            if verdict.get("relevant") is False:
                score = min(score, cutoff - 1)
            listed = verdict.get("matched_entities")
            if isinstance(listed, list):
                anchors = list(
                    dict.fromkeys([*(str(item) for item in listed), *anchors])
                )[:5]
            reason = str(verdict.get("why_this_fits") or "").strip()[:300]
            if not _reason_is_grounded(reason, profile):
                rebuilt = None
                if _has_genuine_match(matched, matched_phrases) and concrete:
                    rebuilt = (
                        f"This listing directly touches your "
                        f"{profile.get('core_domain') or 'concept'} focus on "
                        f"{', '.join(concrete[:3])}."
                    )
                    if not _reason_is_grounded(rebuilt, profile):
                        rebuilt = None
                if rebuilt is None:
                    rebuilt = _venue_reason(haystack, profile)
                    score = 65
                else:
                    score = min(score, 69)
                if not rebuilt:
                    result.rejected_count += 1
                    continue
                reason = rebuilt
            if score < cutoff or not reason:
                result.rejected_count += 1
                continue

        metadata["why_this_fits"] = reason
        metadata["matched_terms"] = anchors[:5]
        metadata["match_score"] = round(min(1.0, score / 100), 2)
        candidate["decision_metadata"] = metadata
        result.candidates.append(candidate)
        result.accepted_count += 1

    if verdicts:
        result.note = f"{result.llm_verified_count} explanations verified by Groq"
    else:
        result.note = "Groq unavailable; only exact concept matches were kept"
    return result


def filter_market_signals(
    signals: List[Any],
    profile: Dict[str, Any],
) -> List[Any]:
    """Drop generic legacy news/trend signals and explain the survivors."""

    focus = _focus_tokens(profile)
    kept: List[Any] = []
    for signal in signals:
        signal_type = str(getattr(signal, "signal_type", "") or "")
        if signal_type not in {"news", "trend"}:
            kept.append(signal)
            continue
        text = (
            f"{getattr(signal, 'title', '') or ''} "
            f"{getattr(signal, 'summary', '') or ''}"
        )
        matched = _matched_focus(text, focus)
        phrases = _matched_phrases(text, profile)
        concrete = _concrete_terms(phrases, matched, signal_type)
        if not _has_genuine_match(matched, phrases, signal_type) or not concrete:
            continue
        reason = (
            f"Mentions {', '.join(concrete[:3])}, which connects directly to "
            f"your {profile.get('core_domain') or 'concept'} focus."
        )
        if not _reason_is_grounded(reason, profile, signal_type):
            continue
        summary = str(getattr(signal, "summary", "") or "")
        signal.summary = f"{summary[:1200]} Why it fits: {reason}".strip()
        signal.keywords = concrete[:5] or list(getattr(signal, "keywords", []) or [])[:5]
        kept.append(signal)
    return kept


async def search_concept_intel(
    profile: Dict[str, Any],
    *,
    language: str = "en",
) -> ConceptIntelResult:
    """Run four constrained searches and gate every result before the UI."""

    result = ConceptIntelResult()
    plans = search_plans(profile)
    limit = max(3, settings.RADAR_INTEL_MAX_RESULTS)
    key = (settings.TAVILY_API_KEY or "").strip()
    fallback_buckets: List[str] = []
    outcomes: List[Any]

    try:
        async with httpx.AsyncClient(
            timeout=max(10.0, settings.EXTERNAL_SIGNAL_TIMEOUT_SECONDS * 3)
        ) as client:
            if key:
                outcomes = await asyncio.gather(
                    *(
                        _tavily_search(client, plan["query"], plan["options"], limit)
                        for plan in plans
                    ),
                    return_exceptions=True,
                )
            else:
                outcomes = [Exception("Tavily API key is not configured") for _ in plans]

            # Tavily free tiers can return HTTP 432 during a burst. News and
            # trends still have a real public source: Google News RSS links to
            # dated articles. The same strict concept verification still runs.
            for index, (plan, outcome) in enumerate(zip(plans, outcomes)):
                if plan["bucket"] not in {"trends", "news"}:
                    continue
                if not isinstance(outcome, Exception) and outcome:
                    continue
                try:
                    fallback_items = await _rss_search(client, plan, profile, limit)
                except Exception as exc:  # noqa: BLE001 - network boundary
                    logger.warning(
                        "Google News RSS fallback failed for %s: %s", plan["bucket"], exc
                    )
                    continue
                if fallback_items:
                    outcomes[index] = fallback_items
                    fallback_buckets.append(plan["bucket"])
    except Exception as exc:  # noqa: BLE001 - network boundary
        result.note = f"Search unavailable: {type(exc).__name__}"
        outcomes = [Exception(result.note) for _ in plans]

    if fallback_buckets:
        result.note = (
            "Tavily was unavailable for "
            f"{', '.join(sorted(set(fallback_buckets)))}; "
            "Google News RSS was used with the same concept verification."
        )
    elif not key:
        result.note = "Tavily API key is not configured; direct platform adapters only."

    for plan, outcome in zip(plans, outcomes):
        provider = "tavily"
        if isinstance(outcome, list) and outcome:
            provider = str(outcome[0].get("provider") or "tavily") if isinstance(outcome[0], dict) else "tavily"
        source_id = f"{provider}_{plan['bucket']}"
        if provider == "google_news_rss":
            label = f"Google News RSS · {plan['bucket'].title()}"
        else:
            label = f"Tavily · {plan['bucket'].title()}"

        if isinstance(outcome, Exception):
            note = f"Search failed: {type(outcome).__name__}"
            result.sources.append(
                {
                    "source": source_id,
                    "label": label,
                    "status": "error",
                    "raw_count": 0,
                    "accepted_count": 0,
                    "note": note,
                }
            )
            result.plans.append(
                {
                    "intent": plan["bucket"],
                    "query": plan["query"],
                    "raw_results": 0,
                    "note": note,
                }
            )
            continue

        result.raw_count += len(outcome)
        gated: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for raw in outcome:
            if not isinstance(raw, dict):
                continue
            item = _normalise_raw(
                raw,
                bucket=plan["bucket"],
                query=plan["query"],
                min_score=float(
                    plan["options"].get("min_score", settings.RADAR_TAVILY_MIN_SCORE)
                ),
            )
            if item is None or item["url"].rstrip("/").lower() in seen:
                continue
            seen.add(item["url"].rstrip("/").lower())
            gated.append(item)

        result.gated_count += len(gated)
        result.sources.append(
            {
                "source": source_id,
                "label": label,
                "status": "ok" if outcome else "empty",
                "raw_count": len(outcome),
                "accepted_count": 0,
                "note": (
                    "public article links; strict concept verification applied"
                    if provider == "google_news_rss"
                    else "score >= %.2f"
                    % float(
                        plan["options"].get("min_score", settings.RADAR_TAVILY_MIN_SCORE)
                    )
                ),
            }
        )
        result.plans.append(
            {
                "intent": plan["bucket"],
                "query": plan["query"],
                "raw_results": len(outcome),
                "actionable_after_gatekeeper": len(gated),
                "note": (
                    "Google News RSS fallback; strict concept verification applied"
                    if provider == "google_news_rss"
                    else "Enriched with Groq relevance gatekeeper"
                    if groq_client.configured
                    else "Heuristic relevance gate"
                ),
            }
        )
        result.items.extend(gated)

    # Dedupe across buckets; a single URL should never appear twice.
    unique: Dict[str, Dict[str, Any]] = {}
    for item in result.items:
        unique.setdefault(item["url"].rstrip("/").lower(), item)
    candidates = list(unique.values())

    accepted, verified_count = await _verify_items(candidates, profile, language)
    result.items = accepted
    result.accepted_count = len(accepted)
    result.rejected_count = max(0, result.gated_count - result.accepted_count)
    result.llm_verified_count = verified_count
    accepted_by_source: Dict[str, int] = {}
    for item in accepted:
        source = f"{item.get('provider') or 'tavily'}_{item['bucket']}"
        accepted_by_source[source] = accepted_by_source.get(source, 0) + 1
    for source in result.sources:
        source["accepted_count"] = accepted_by_source.get(source["source"], 0)
    for plan in result.plans:
        plan["accepted"] = (
            accepted_by_source.get(f"tavily_{plan['intent']}", 0)
            + accepted_by_source.get(f"google_news_rss_{plan['intent']}", 0)
        )
    return result
