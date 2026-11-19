"""Direct, source-linked opportunity discovery for the Radar idea input.

This module is deliberately retrieval-first: every card it emits is backed by a
record returned from a live platform endpoint (or a clearly-labelled discovery
feed). It never invents a title, organiser, deadline, reward, or link. Adapters
normalise each provider into the existing opportunity-candidate shape and attach
provenance so the UI can say exactly where a result came from and whether the
user still needs to verify it on the official page.
"""

from __future__ import annotations

import asyncio
import html
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

import httpx

from app.core.config import settings

_PERSONA_TERMS: Dict[str, Tuple[str, ...]] = {
    "tech_builder": (
        "ai", "machine learning", "ml", "llm", "agent", "robotics", "software",
        "developer", "devtools", "open source", "data", "cybersecurity", "cloud",
    ),
    "design_biotech": (
        "bio", "biotech", "genomics", "health", "medical", "clinical", "drug",
        "diagnostic", "lab", "protein", "patient", "therapeutic", "pharma",
    ),
    "policy_law": (
        "policy", "law", "legal", "governance", "regulation", "compliance",
        "competition", "privacy", "justice", "public", "policy brief", "antitrust",
    ),
    "business_finance": (
        "finance", "fintech", "venture", "startup", "market", "trading", "grant",
        "funding", "investor", "defi", "quant", "revenue",
    ),
}

_STOPWORDS = {
    "about", "across", "after", "again", "against", "also", "and", "any", "are",
    "build", "building", "can", "could", "for", "from", "have", "help", "into",
    "its", "make", "many", "more", "most", "our", "out", "over", "project",
    "should", "some", "solution", "that", "the", "their", "this", "through",
    "tool", "using", "want", "was", "were", "what", "when", "where", "which",
    "with", "would", "your", "students", "student", "idea", "work", "need",
}

_DATE_IN_TEXT = re.compile(
    r"(?:[A-Za-z]{3,9}\s+\d{1,2},?\s+20\d{2}|\d{1,2}/\d{1,2}/20\d{2}|20\d{2}-\d{2}-\d{2})"
)
_TAG_RE = re.compile(r"<[^>]+>")
_MONEY_RE = re.compile(r"(?:US)?\$\s?[\d,.]+(?:\s?(?:k|m|million|billion))?", re.IGNORECASE)
_REGISTRATION_HINT = re.compile(
    r"(?:regist(?:er|ration|rations)\s*(?:by|closes?|ends?|deadline)|apply\s+by|"
    r"applications?\s+close|submissions?\s+close|last\s+date\s+to\s+(?:apply|register)|deadline)",
    re.IGNORECASE,
)
_HTML_DATE_FORMATS = (
    "%b %d, %Y", "%B %d, %Y", "%b %d %Y", "%B %d %Y", "%d %b %Y", "%d %B %Y",
    "%m/%d/%Y", "%m-%d-%Y", "%Y/%m/%d", "%Y-%m-%d",
)

# Several public endpoints reject generic python-http clients. Browser-like
# headers keep the adapters on the same code path as a normal visitor without
# faking identity or using credentials.
_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}


@dataclass
class SourceResult:
    source: str
    label: str
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    raw_count: int = 0
    status: str = "empty"
    is_official: bool = False
    note: Optional[str] = None


@dataclass
class DiscoveryResult:
    query: str
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[SourceResult] = field(default_factory=list)

    def source_payload(self) -> List[Dict[str, Any]]:
        return [
            {
                "source": item.source,
                "label": item.label,
                "status": item.status,
                "raw_count": item.raw_count,
                "accepted_count": len(item.candidates),
                "is_official": item.is_official,
                "note": item.note,
            }
            for item in self.sources
        ]


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(_clean_text(item) for item in value if item is not None)
    if isinstance(value, dict):
        return ", ".join(
            f"{key}: {_clean_text(item)}" for key, item in value.items() if item is not None
        )
    text = _TAG_RE.sub(" ", str(value))
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _parse_flexible_date(value: Any) -> Optional[datetime]:
    """Parse a date without guessing missing years or months."""

    if isinstance(value, datetime):
        return _as_utc(value)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        return None

    raw = value.strip().replace("Z", "+00:00")
    try:
        return _as_utc(datetime.fromisoformat(raw))
    except ValueError:
        pass

    matches = _DATE_IN_TEXT.findall(raw)
    for candidate in reversed(matches):
        normalised = candidate.replace(",", "").strip()
        for fmt in _HTML_DATE_FORMATS:
            try:
                parsed = datetime.strptime(normalised, fmt.replace(",", ""))
                return parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def _future_deadline(value: Any, now: datetime) -> Optional[datetime]:
    parsed = _parse_flexible_date(value)
    if parsed is None or parsed <= now:
        return None
    if parsed.time() == datetime.min.time():
        parsed = parsed.replace(hour=23, minute=59)
    return parsed


def _end_of_event_date(value: Any) -> Optional[date]:
    parsed = _parse_flexible_date(value)
    return parsed.date() if parsed else None


def _currency(value: Any) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    match = _MONEY_RE.search(text)
    if not match:
        return None
    amount = re.sub(r"\$\s+", "$", match.group(0).strip())
    return amount if "$" in amount else f"${amount}"


def _extract_terms(idea: str, persona: str) -> Tuple[List[str], List[str]]:
    tokens = re.findall(r"[a-z][a-z0-9+#.-]{2,}", (idea or "").lower())
    unique_tokens: List[str] = []
    for token in tokens:
        if token not in _STOPWORDS and token not in unique_tokens:
            unique_tokens.append(token)
    persona_terms = [
        term
        for term in _PERSONA_TERMS.get(persona, _PERSONA_TERMS["tech_builder"])
        if term not in unique_tokens
    ]
    if not unique_tokens:
        unique_tokens = list(persona_terms[:3]) or ["hackathon", "event", "grant"]
    combined = unique_tokens[:6] + persona_terms[:4]
    return list(dict.fromkeys(combined))[:8], unique_tokens[:6]


def _infer_category(title: str, explicit: Optional[str] = None) -> str:
    if explicit:
        value = explicit.strip().lower().replace(" ", "_")
        if value in {"hackathons", "hackathon", "buildathon", "competition"}:
            return "hackathon" if "competition" not in value else "general_event"
        if value in {"grants", "grant", "funding", "fellowship", "scholarship"}:
            return "grant" if "fellowship" not in value else "fellowship"
        if value in {"events", "event", "conference"}:
            return "general_event"
    blob = (title or "").lower()
    if any(word in blob for word in ("hackathon", "buildathon", "build sprint")):
        return "hackathon"
    if any(word in blob for word in ("grant", "funding opportunity", "call for proposals")):
        return "grant"
    if any(word in blob for word in ("fellowship", "residency")):
        return "fellowship"
    return "general_event"


def _make_candidate(
    *,
    source: str,
    label: str,
    title: str,
    url: str,
    deadline: datetime,
    description: str,
    persona: str,
    category: str,
    tags: Sequence[str],
    host_organization: Optional[str],
    city: Optional[str],
    event_date: Optional[date],
    location_type: str,
    reward_pool: Optional[str],
    is_official: bool,
    source_kind: str,
    verification: str,
    deadline_basis: str,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {
        "source": source,
        "source_label": label,
        "source_kind": source_kind,
        "verification": verification,
        "is_official": is_official,
        "is_live": True,
        "deadline_inferred": deadline_basis not in {
            "registration_deadline",
            "submission_period",
            "application_close_date",
            "registration_deadline_in_search_snippet",
        },
        "deadline_basis": deadline_basis,
        "discovered_by": "idea_radar",
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    return {
        "title": title[:250],
        "category": category,
        "canonical_source_url": url,
        "host_organization": (host_organization or None),
        "deadline": _as_utc(deadline),
        "city": (city or None),
        "event_date": event_date,
        "description": (description or title)[:4000],
        "tags": [str(tag) for tag in tags if str(tag).strip()][:8],
        "domain_personas": [persona],
        "location_type": location_type or "virtual",
        "reward_pool": reward_pool,
        "decision_metadata": metadata,
    }


def _match_candidates(candidates: List[Dict[str, Any]], terms: Sequence[str], persona: str) -> None:
    persona_terms = list(_PERSONA_TERMS.get(persona, ()))
    for candidate in candidates:
        blob = " ".join(
            [
                str(candidate.get("title") or ""),
                str(candidate.get("description") or ""),
                " ".join(str(tag) for tag in candidate.get("tags") or []),
            ]
        ).lower()
        matched = [term for term in terms if term in blob]
        basis = "idea_terms" if matched else []
        if not matched:
            matched = [term for term in persona_terms if term in blob]
            basis = "domain_terms" if matched else []
        score = round(min(1.0, 0.15 + (0.17 * len(matched))), 2) if matched else 0.12
        metadata = candidate.setdefault("decision_metadata", {})
        metadata["matched_terms"] = matched[:6]
        metadata["match_basis"] = "keyword" if basis else "broad"
        metadata["match_score"] = score


def _dedupe_key(candidate: Dict[str, Any]) -> str:
    url = str(candidate.get("canonical_source_url") or "")
    try:
        parts = urllib.parse.urlsplit(url)
        path = re.sub(r"/+$", "", parts.path.lower())
        url_key = f"{parts.hostname or ''}{path}"
    except ValueError:
        url_key = url.lower()
    title_key = re.sub(r"[^a-z0-9]+", "", str(candidate.get("title") or "").lower())
    deadline = candidate.get("deadline")
    date_key = deadline.strftime("%Y-%m-%d") if isinstance(deadline, datetime) else ""
    return f"{url_key}|{title_key[:60]}|{date_key}"


def deduplicate_candidates(candidates: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Collapse cross-posted records while preserving the strongest provenance."""

    by_key: Dict[str, Dict[str, Any]] = {}
    for candidate in candidates:
        if not isinstance(candidate, dict) or not candidate.get("canonical_source_url"):
            continue
        key = _dedupe_key(candidate)
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = dict(candidate)
            continue

        def score(item: Dict[str, Any]) -> float:
            return float((item.get("decision_metadata") or {}).get("match_score") or 0)

        if score(candidate) > score(existing):
            merged = dict(candidate)
            merged_tags = list(existing.get("tags") or [])
            merged_personas = list(existing.get("domain_personas") or [])
        else:
            merged = dict(existing)
            merged_tags = list(candidate.get("tags") or [])
            merged_personas = list(candidate.get("domain_personas") or [])

        for tag in (candidate.get("tags") or []) + (existing.get("tags") or []):
            if tag not in merged_tags:
                merged_tags.append(tag)
        for persona in (candidate.get("domain_personas") or []) + (existing.get("domain_personas") or []):
            if persona not in merged_personas:
                merged_personas.append(persona)
        merged["tags"] = merged_tags[:8]
        merged["domain_personas"] = merged_personas[:4]
        for field_name in ("reward_pool", "city", "event_date", "host_organization"):
            if not merged.get(field_name) and (existing.get(field_name) or candidate.get(field_name)):
                merged[field_name] = existing.get(field_name) or candidate.get(field_name)
        by_key[key] = merged

    ranked = sorted(
        by_key.values(),
        key=lambda item: (
            float((item.get("decision_metadata") or {}).get("match_score") or 0),
            -(item.get("deadline").timestamp() if isinstance(item.get("deadline"), datetime) else 0),
        ),
        reverse=True,
    )
    return ranked


async def _devpost_adapter(client: httpx.AsyncClient, terms: Sequence[str], persona: str, now: datetime, limit: int) -> SourceResult:
    result = SourceResult(source="devpost", label="Devpost", is_official=True)
    response = await client.get(
        "https://devpost.com/api/hackathons",
        params={"status": "open", "amount": max(limit, 20)},
        headers=_HTTP_HEADERS,
    )
    response.raise_for_status()
    items = (response.json() or {}).get("hackathons") or []
    result.raw_count = len(items)
    for item in items[:limit]:
        title = _clean_text(item.get("title"))
        url = _clean_text(item.get("url"))
        if not title or not url:
            continue
        if url.startswith("//"):
            url = f"https:{url}"
        elif url.startswith("/"):
            url = f"https://devpost.com{url}"
        dates = _clean_text(item.get("submission_period_dates"))
        deadline = _future_deadline(dates, now)
        if not deadline:
            continue
        themes = [
            _clean_text(theme.get("name")) if isinstance(theme, dict) else _clean_text(theme)
            for theme in item.get("themes") or []
        ]
        location = _clean_text((item.get("displayed_location") or {}).get("location"))
        location_type = "virtual" if "online" in location.lower() else ("hybrid" if "hybrid" in location.lower() else "in_person")
        description_parts = [
            f"Host: {_clean_text(item.get('organization_name'))}" if item.get("organization_name") else "",
            f"Themes: {', '.join(themes)}" if themes else "",
            f"Submission period: {dates}" if dates else "",
            f"Time left: {_clean_text(item.get('time_left_to_submission'))}" if item.get("time_left_to_submission") else "",
        ]
        result.candidates.append(
            _make_candidate(
                source="devpost",
                label="Devpost",
                title=title,
                url=url,
                deadline=deadline,
                description=" | ".join(part for part in description_parts if part),
                persona=persona,
                category="hackathon",
                tags=themes,
                host_organization=_clean_text(item.get("organization_name")) or None,
                city=None if location_type == "virtual" else location or None,
                event_date=_end_of_event_date(_DATE_IN_TEXT.findall(dates)[0]) if dates and _DATE_IN_TEXT.findall(dates) else None,
                location_type=location_type,
                reward_pool=_currency(item.get("prize_amount")),
                is_official=True,
                source_kind="public_api",
                verification="official_page",
                deadline_basis="submission_period",
            )
        )
    result.status = "ok" if result.candidates else "empty"
    if result.raw_count and not result.candidates:
        result.note = "Open hackathons found, but none exposed a parseable future deadline."
    return result


async def _unstop_adapter(client: httpx.AsyncClient, terms: Sequence[str], persona: str, now: datetime, limit: int) -> SourceResult:
    result = SourceResult(source="unstop", label="Unstop", is_official=True)
    response = await client.get(
        "https://unstop.com/api/public/opportunity/search-result",
        params={"opportunity": "hackathons", "page": 1, "per_page": min(limit, 10), "oppstatus": "open"},
        headers={**_HTTP_HEADERS, "Referer": "https://unstop.com/hackathons"},
    )
    response.raise_for_status()
    payload = response.json() or {}
    items = ((payload.get("data") or {}).get("data")) or []
    result.raw_count = len(items)
    for item in items[:limit]:
        title = _clean_text(item.get("title"))
        url = _clean_text(item.get("seo_url"))
        if not url and item.get("public_url"):
            url = f"https://unstop.com/{str(item['public_url']).lstrip('/')}"
        if not title or not url:
            continue
        deadline = _future_deadline(item.get("end_date"), now)
        if not deadline:
            continue
        skills = [
            _clean_text(skill.get("skill_name") or skill.get("skill"))
            if isinstance(skill, dict) else _clean_text(skill)
            for skill in item.get("required_skills") or []
        ]
        address = item.get("address_with_country_logo") or {}
        city = _clean_text(address.get("city")) if isinstance(address, dict) else ""
        region = _clean_text(item.get("region"))
        location_type = "virtual" if region.lower() in {"online", "remote"} else ("hybrid" if region.lower() == "hybrid" else "in_person")
        organisation = item.get("organisation") or {}
        host = _clean_text(organisation.get("name")) if isinstance(organisation, dict) else ""
        result.candidates.append(
            _make_candidate(
                source="unstop",
                label="Unstop",
                title=title,
                url=url,
                deadline=deadline,
                description=_clean_text(item.get("details"))[:1000] or title,
                persona=persona,
                category=_infer_category(title, "hackathons"),
                tags=skills,
                host_organization=host or None,
                city=city or None,
                event_date=_end_of_event_date(item.get("start_date")),
                location_type=location_type,
                reward_pool=_currency(json.dumps(item.get("prizes") or "")),
                is_official=True,
                source_kind="public_api",
                verification="official_page",
                deadline_basis="registration_deadline",
            )
        )
    result.status = "ok" if result.candidates else "empty"
    if result.raw_count and not result.candidates:
        result.note = "Open listings found, but none exposed a parseable future deadline."
    return result


async def _luma_adapter(client: httpx.AsyncClient, terms: Sequence[str], persona: str, now: datetime, limit: int) -> SourceResult:
    result = SourceResult(source="luma", label="Luma", is_official=True)
    query = " ".join(terms[:4])
    response = await client.get(
        "https://api.lu.ma/discover/get-paginated-events",
        params={"pagination_limit": max(limit, 20), "query": query},
        headers=_HTTP_HEADERS,
    )
    response.raise_for_status()
    entries = (response.json() or {}).get("entries") or []
    result.raw_count = len(entries)
    # Luma's public discovery payload exposes event start/end times but no
    # registration deadline. An event date is not a registration date, so these
    # records are not promoted to the upcoming-registration Radar feed.
    result.status = "empty"
    result.note = (
        f"Events found for '{query}', but Luma does not expose a registration deadline; "
        "no cards were created."
        if result.raw_count
        else f"No Luma events found for '{query}'."
    )
    return result


def _extract_mlh_events(html: str) -> List[Dict[str, Any]]:
    match = re.search(r'<script\s+data-page="app"\s+type="application/json">(.*?)</script>', html, re.S)
    if not match:
        return []
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    return list(((payload.get("props") or {}).get("upcomingEvents")) or [])


async def _mlh_adapter(client: httpx.AsyncClient, terms: Sequence[str], persona: str, now: datetime, limit: int) -> SourceResult:
    result = SourceResult(source="mlh", label="Major League Hacking", is_official=True)
    year = now.year
    items: List[Dict[str, Any]] = []
    for season_year in (year, year + 1):
        response = await client.get(
            f"https://www.mlh.com/seasons/{season_year}/events",
            headers=_HTTP_HEADERS,
        )
        response.raise_for_status()
        items = _extract_mlh_events(str(response.text))
        if items:
            break
    result.raw_count = len(items)
    # MLH season pages publish event windows, not registration close dates.
    # Showing an event end as a registration deadline would be misleading.
    result.status = "empty"
    result.note = (
        "Season events found, but MLH does not expose a registration deadline; "
        "no cards were created."
        if result.raw_count
        else "No MLH season events found."
    )
    return result


async def _grants_adapter(client: httpx.AsyncClient, terms: Sequence[str], persona: str, now: datetime, limit: int) -> SourceResult:
    result = SourceResult(source="grants_gov", label="Grants.gov", is_official=True)
    keyword = " ".join(terms[:3])
    response = await client.post(
        "https://api.grants.gov/v1/api/search2",
        json={
            "keyword": keyword,
            "oppStatuses": "forecasted|posted",
            "rows": max(limit, 20),
            "startRecordNum": 0,
        },
        headers=_HTTP_HEADERS,
        timeout=max(12.0, settings.RADAR_DIRECT_SOURCE_TIMEOUT_SECONDS),
    )
    response.raise_for_status()
    hits = ((response.json() or {}).get("data") or {}).get("oppHits") or []
    result.raw_count = len(hits)
    for hit in hits[:limit]:
        title = _clean_text(hit.get("title"))
        opportunity_id = _clean_text(hit.get("id"))
        if not title or not opportunity_id:
            continue
        deadline = _future_deadline(hit.get("closeDate"), now)
        if not deadline:
            continue
        categories = _clean_text(hit.get("fundingCategories"))
        result.candidates.append(
            _make_candidate(
                source="grants_gov",
                label="Grants.gov",
                title=title,
                url=f"https://www.grants.gov/search-results-detail/{opportunity_id}",
                deadline=deadline,
                description=" | ".join(
                    part for part in (
                        f"Agency: {_clean_text(hit.get('agencyName'))}" if hit.get("agencyName") else "",
                        f"Opportunity number: {_clean_text(hit.get('number'))}" if hit.get("number") else "",
                        f"Status: {_clean_text(hit.get('oppStatus'))}" if hit.get("oppStatus") else "",
                        f"Funding category: {categories}" if categories else "",
                    ) if part
                ),
                persona=persona,
                category="grant",
                tags=[tag.strip() for tag in categories.split(",") if tag.strip()][:6],
                host_organization=_clean_text(hit.get("agencyName")) or None,
                city=None,
                event_date=_end_of_event_date(hit.get("openDate")),
                location_type="virtual",
                reward_pool=None,
                is_official=True,
                source_kind="public_api",
                verification="official_page",
                deadline_basis="application_close_date",
            )
        )
    result.status = "ok" if result.candidates else "empty"
    if result.raw_count and not result.candidates:
        result.note = f"Grant records found for '{keyword}', but none had a future close date."
    return result


def _rss_items(xml_text: str) -> List[Dict[str, str]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    items: List[Dict[str, str]] = []
    for item in root.findall(".//item"):
        items.append(
            {
                "title": _clean_text(item.findtext("title")),
                "url": _clean_text(item.findtext("link")),
                "description": _clean_text(item.findtext("description")),
                "published": _clean_text(item.findtext("pubDate")),
            }
        )
    return items


async def _commudle_adapter(client: httpx.AsyncClient, terms: Sequence[str], persona: str, now: datetime, limit: int) -> SourceResult:
    result = SourceResult(
        source="commudle",
        label="Commudle (news discovery)",
        is_official=False,
    )
    query = f"site:commudle.com (hackathon OR event) {' '.join(terms[:4])}"
    response = await client.get(
        "https://news.google.com/rss/search",
        params={"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"},
        headers=_HTTP_HEADERS,
    )
    response.raise_for_status()
    items = _rss_items(str(response.text))
    result.raw_count = len(items)
    for item in items[:limit]:
        title = _clean_text(item.get("title")).replace(" - Google News", "").strip()
        url = _clean_text(item.get("url"))
        if not title or not url:
            continue
        snippet = f"{title} {item.get('description') or ''}"
        date_match = _DATE_IN_TEXT.search(snippet)
        if not _REGISTRATION_HINT.search(snippet) or not date_match:
            continue
        deadline = _future_deadline(date_match.group(0), now)
        if not deadline:
            continue
        result.candidates.append(
            _make_candidate(
                source="commudle",
                label="Commudle (news discovery)",
                title=title,
                url=url,
                deadline=deadline,
                description=_clean_text(item.get("description")) or title,
                persona=persona,
                category=_infer_category(title),
                tags=[],
                host_organization="Commudle",
                city=None,
                event_date=_end_of_event_date(item.get("published")) if item.get("published") else None,
                location_type="virtual",
                reward_pool=None,
                is_official=False,
                source_kind="search_discovery",
                verification="verify_on_official_page",
                deadline_basis="registration_deadline_in_search_snippet",
                extra_metadata={"discovery_query": query},
            )
        )
    result.status = "ok" if result.candidates else "empty"
    result.note = (
        "Commudle has no public event API; results are news-discovery links and must be verified on the official page."
        if result.raw_count
        else "No Commudle discovery links found for this idea."
    )
    return result


async def _hackalendar_adapter(client: httpx.AsyncClient, terms: Sequence[str], persona: str, now: datetime, limit: int) -> SourceResult:
    result = SourceResult(source="hackalendar", label="Hackalendar", is_official=False)
    response = await client.get(
        "https://hackalendar.com/api/events",
        headers=_HTTP_HEADERS,
    )
    response.raise_for_status()
    payload = response.json() or {}
    items = payload.get("data") if isinstance(payload, dict) else payload
    items = items or []
    result.raw_count = len(items)
    for item in items[:limit]:
        title = _clean_text(item.get("name"))
        url = _clean_text(item.get("url"))
        if not title or not url:
            continue
        deadline = _future_deadline(item.get("registrationDeadline"), now)
        if not deadline:
            continue
        city = _clean_text(item.get("cityLabel") or item.get("city"))
        themes = [_clean_text(theme) for theme in item.get("themes") or [] if _clean_text(theme)]
        result.candidates.append(
            _make_candidate(
                source="hackalendar",
                label="Hackalendar",
                title=title,
                url=url,
                deadline=deadline,
                description=_clean_text(item.get("description")) or title,
                persona=persona,
                category=_infer_category(title),
                tags=themes,
                host_organization=_clean_text(item.get("organizer")) or None,
                city=city or None,
                event_date=_end_of_event_date(item.get("startAt")),
                location_type="virtual" if str(item.get("mode") or "").lower() in {"online", "virtual"} else "in_person",
                reward_pool=_currency(item.get("prizePool")),
                is_official=False,
                source_kind="aggregator",
                verification="verify_on_official_page",
                deadline_basis="registration_deadline",
            )
        )
    result.status = "ok" if result.candidates else "empty"
    if result.raw_count and not result.candidates:
        result.note = "Aggregated events found, but none exposed a future registration deadline."
    return result


_SOURCE_LABELS = {
    "devpost": "Devpost",
    "mlh": "Major League Hacking",
    "unstop": "Unstop",
    "luma": "Luma",
    "grants_gov": "Grants.gov",
    "commudle": "Commudle (news discovery)",
    "hackalendar": "Hackalendar",
}

_ADAPTERS = (
    ("devpost", _devpost_adapter),
    ("mlh", _mlh_adapter),
    ("unstop", _unstop_adapter),
    ("luma", _luma_adapter),
    ("grants_gov", _grants_adapter),
    ("commudle", _commudle_adapter),
    ("hackalendar", _hackalendar_adapter),
)


async def discover_opportunities(
    *,
    raw_idea: str,
    persona: str,
    client: Optional[httpx.AsyncClient] = None,
) -> DiscoveryResult:
    """Fetch, normalise, match, and dedupe real opportunities for an idea."""

    now = datetime.now(timezone.utc)
    terms, _ = _extract_terms(raw_idea, persona)
    query = " ".join(terms[:5])
    limit = max(1, settings.RADAR_DIRECT_SOURCE_LIMIT)

    owns_client = client is None
    http_client = client or httpx.AsyncClient(
        timeout=settings.RADAR_DIRECT_SOURCE_TIMEOUT_SECONDS,
        follow_redirects=True,
    )
    try:
        if not settings.RADAR_ENABLE_DIRECT_SOURCES:
            return DiscoveryResult(query=query, sources=[])
        tasks = [
            adapter(http_client, terms, persona, now, limit)
            for _, adapter in _ADAPTERS
        ]
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        if owns_client:
            await http_client.aclose()

    sources: List[SourceResult] = []
    candidates: List[Dict[str, Any]] = []
    for (source_name, _), outcome in zip(_ADAPTERS, outcomes):
        if isinstance(outcome, BaseException):
            sources.append(
                SourceResult(
                    source=source_name,
                    label=_SOURCE_LABELS.get(source_name, source_name.replace("_", " ").title()),
                    status="error",
                    note=f"Unavailable ({type(outcome).__name__})",
                )
            )
            continue
        sources.append(outcome)
        candidates.extend(outcome.candidates)

    _match_candidates(candidates, terms, persona)
    deduped = deduplicate_candidates(candidates)
    return DiscoveryResult(query=query, candidates=deduped, sources=sources)


__all__ = [
    "DiscoveryResult",
    "SourceResult",
    "deduplicate_candidates",
    "discover_opportunities",
]
