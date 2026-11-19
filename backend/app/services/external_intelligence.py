"""Cross-platform market and competitor intelligence.

The service treats Tavily/Exa as an optional *search grounding* layer over
platform-specific queries. It never invents posts, startups, or metrics: when
no provider key is configured (or a provider fails), it returns real, openable
search/exploration URLs for each platform and marks them ``is_live=False``.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import quote_plus

import httpx

from app.core.config import settings
from app.schemas.signals import (
    BuilderMatch,
    MarketIntelligenceResponse,
    MarketSignal,
    SignalSource,
    SourceCoverage,
)

logger = logging.getLogger(__name__)

DIRECTORY_SOURCES: Tuple[str, ...] = ("founderdb", "ideabrowser", "tumrr")
TREND_SOURCES: Tuple[str, ...] = ("google_trends",)
SOCIAL_SOURCES: Tuple[str, ...] = ("x", "reddit", "threads")
SUPPORTED_SOURCES: Tuple[str, ...] = DIRECTORY_SOURCES + TREND_SOURCES + SOCIAL_SOURCES

SOURCE_LABELS: Dict[str, str] = {
    "founderdb": "FounderDB",
    "ideabrowser": "IdeaBrowser",
    "tumrr": "Tumrr",
    "google_trends": "Google Trends",
    "x": "X",
    "reddit": "Reddit",
    "threads": "Threads",
    "news": "News",
    "hackernews": "Hacker News",
    "indiehackers": "Indie Hackers",
    "builder": "Builder",
}

_LANDING_URLS: Dict[str, str] = {
    "founderdb": "https://www.founderdb.com/",
    "ideabrowser": "https://www.ideabrowser.com/",
    "tumrr": "https://tumrr.com/",
    "google_trends": "https://trends.google.com/trends/",
    "x": "https://x.com/",
    "reddit": "https://www.reddit.com/",
    "threads": "https://www.threads.net/",
}

_QUERY_TEMPLATES: Dict[str, str] = {
    "founderdb": 'site:founderdb.com ({kw}) startup OR founder OR launch',
    "ideabrowser": 'site:ideabrowser.com ({kw}) idea OR startup OR product',
    "tumrr": 'site:tumrr.com ({kw}) startup OR product OR indie',
    "x": 'site:x.com ({kw}) building OR launched OR "pain point"',
    "reddit": 'site:reddit.com ({kw}) discussion OR "looking for" OR alternative',
    "threads": 'site:threads.net ({kw}) builder OR launched OR prototype',
}

_SOCIAL_SOURCES = set(SOCIAL_SOURCES)


def _signal_id(source: str, url: str) -> str:
    return hashlib.sha1(f"{source}|{url}".encode("utf-8")).hexdigest()[:12]


def _parse_published_at(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def _normalise_url(url: str) -> str:
    """Lower-case a URL and drop cosmetic host/slash differences for dedup."""

    value = url.strip().rstrip("/").lower()
    if "://" in value:
        scheme, rest = value.split("://", 1)
        if rest.startswith("www."):
            rest = rest[4:]
        value = f"{scheme}://{rest}"
    return value


class ExternalIntelligenceService:
    """Collects signals without assuming access to any single platform API."""

    def __init__(self, client: Optional[httpx.AsyncClient] = None) -> None:
        self._client = client

    async def _search_provider(
        self,
        query: str,
        max_results: int,
        *,
        search_depth: Optional[str] = None,
        time_range: Optional[str] = None,
        filter_by_published_date: Optional[bool] = None,
        include_published_date: Optional[bool] = None,
        include_domains: Optional[Sequence[str]] = None,
        topic: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search with Tavily first; only fall back to Exa when Tavily yields nothing.

        Keeping a single provider per query prevents double-counted results and
        makes the configured primary explicit. Both providers are treated as
        grounding layers only: their results are normalised into real URLs and
        no post, startup, or metric is synthesised locally.

        Keyword-only options are forwarded to Tavily's advanced recency filters.
        They are optional so existing callers keep working unchanged.
        """

        client = self._client
        owns_client = client is None
        if client is None:
            timeout = max(2.0, float(settings.EXTERNAL_SIGNAL_TIMEOUT_SECONDS))
            client = httpx.AsyncClient(timeout=timeout)

        tavily_payload: Dict[str, Any] = {
            "api_key": settings.TAVILY_API_KEY,
            "query": query,
            "search_depth": search_depth or "basic",
            "include_answer": False,
            "max_results": max_results,
        }
        if time_range:
            tavily_payload["time_range"] = time_range
        if filter_by_published_date is not None:
            tavily_payload["filter_by_published_date"] = filter_by_published_date
        if include_published_date is not None:
            tavily_payload["include_published_date"] = include_published_date
        if include_domains:
            tavily_payload["include_domains"] = list(include_domains)
        if topic:
            tavily_payload["topic"] = topic

        exa_payload: Dict[str, Any] = {
            "query": query,
            "numResults": max_results,
            "contents": {"text": True, "summary": True},
        }
        if include_domains:
            exa_payload["includeDomains"] = list(include_domains)

        async def tavily_search() -> List[Dict[str, Any]]:
            response = await client.post("https://api.tavily.com/search", json=tavily_payload)
            response.raise_for_status()
            payload = response.json()
            return list(payload.get("results") or [])

        async def exa_search() -> List[Dict[str, Any]]:
            response = await client.post(
                "https://api.exa.ai/search",
                headers={
                    "x-api-key": settings.EXA_API_KEY,
                    "Content-Type": "application/json",
                },
                json=exa_payload,
            )
            response.raise_for_status()
            payload = response.json()
            return list(payload.get("results") or [])

        try:
            providers: Tuple[Tuple[str, Any], ...] = (
                ("tavily", tavily_search),
                ("exa", exa_search),
            )
            for name, provider in providers:
                key = settings.TAVILY_API_KEY if name == "tavily" else settings.EXA_API_KEY
                if not key:
                    continue
                try:
                    results = await provider()
                except Exception as exc:
                    logger.warning("%s grounded search failed: %s", name.title(), exc)
                    continue
                if results:
                    return results
        finally:
            if owns_client:
                await client.aclose()

        return []

    async def search_for_intent(
        self,
        query: str,
        *,
        intent: str,
        max_age_hours: int = 0,
        max_results: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Run an intent-specific Tavily (primary) / Exa (fallback) search.

        Hackathon and builder intents are locked to their platform allowlists;
        the news intent uses Tavily's news topic. ``max_age_hours`` is a local
        post-filter on provider-published dates (0 keeps the provider's own
        day/week/month recency window and bypasses any local cache).
        """

        limit = max_results or settings.RADAR_TAVILY_MAX_RESULTS
        options: Dict[str, Any] = {
            "search_depth": settings.RADAR_TAVILY_SEARCH_DEPTH,
            "filter_by_published_date": settings.RADAR_TAVILY_FILTER_BY_PUBLISHED_DATE,
            "include_published_date": settings.RADAR_TAVILY_INCLUDE_PUBLISHED_DATE,
        }

        if intent == "news":
            options["topic"] = "news"
            options["time_range"] = settings.RADAR_TAVILY_NEWS_TIME_RANGE
        elif intent == "hackathons":
            options["time_range"] = settings.RADAR_TAVILY_TIME_RANGE
            options["include_domains"] = list(settings.RADAR_HACKATHON_DOMAINS)
        elif intent == "builders":
            options["time_range"] = settings.RADAR_TAVILY_TIME_RANGE
            options["include_domains"] = list(settings.RADAR_BUILDER_DOMAINS)
        else:
            options["time_range"] = settings.RADAR_TAVILY_TIME_RANGE

        raw_results = await self._search_provider(query, limit, **options)
        if max_age_hours <= 0:
            return raw_results

        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        filtered: List[Dict[str, Any]] = []
        for item in raw_results:
            published = _parse_published_at(
                item.get("published_date") or item.get("publishedDate")
            )
            if published is None or published >= cutoff:
                filtered.append(item)
        return filtered

    def _fallback_signal(self, source: str, keywords: Sequence[str]) -> MarketSignal:
        """Return a real link the student can open to verify the source manually."""

        label = SOURCE_LABELS[source]
        primary = keywords[0] if keywords else label
        topic = ", ".join(keywords[:3]) if keywords else label
        encoded = quote_plus(primary)

        if source == "google_trends":
            url = f"https://trends.google.com/trends/explore?q={encoded}"
            title = f"Google Trends · {primary}"
            summary = (
                f"Explore search interest for {topic} over time and by region. "
                "Google Trends needs an interactive session, so no interest values are inferred here."
            )
            signal_type = "trend"
        elif source == "reddit":
            url = f"https://www.reddit.com/search/?q={encoded}&sort=new"
            title = f"Reddit · recent threads on {primary}"
            summary = f"Open live Reddit discussions about {topic} to spot unmet needs and vocabulary."
            signal_type = "discussion"
        elif source == "x":
            url = f"https://x.com/search?q={encoded}&f=live"
            title = f"X · live posts on {primary}"
            summary = f"Open live X posts about {topic} to see launches, complaints, and builder discourse."
            signal_type = "discussion"
        elif source == "threads":
            url = f"https://www.threads.net/search?q={encoded}"
            title = f"Threads · builders discussing {primary}"
            summary = f"Open Threads search for {topic} to find adjacent builders and product chatter."
            signal_type = "discussion"
        else:
            url = _LANDING_URLS[source]
            title = f"{label} · browse similar products"
            summary = f"Open {label} to compare live and early-stage products adjacent to {topic}."
            signal_type = "competitor"

        return MarketSignal(
            id=_signal_id(source, url),
            source=source,  # type: ignore[arg-type]
            signal_type=signal_type,  # type: ignore[arg-type]
            title=title,
            summary=summary,
            url=url,
            relevance_score=0.3,
            keywords=list(keywords[:3]),
            is_live=False,
        )

    def _normalise_result(
        self,
        source: str,
        raw: Dict[str, Any],
        keywords: Sequence[str],
        fallback_url: str,
    ) -> Optional[MarketSignal]:
        title = str(raw.get("title") or "").strip()
        url = str(raw.get("url") or "").strip() or fallback_url
        summary = str(
            raw.get("content")
            or raw.get("summary")
            or raw.get("text")
            or ""
        ).strip()
        if not title and not summary:
            return None

        haystack = f"{title} {summary}".lower()
        matched = [keyword for keyword in keywords if keyword.lower() in haystack]

        try:
            provider_score = float(raw.get("score") or 0.0)
        except (TypeError, ValueError):
            provider_score = 0.0

        relevance = round(
            min(1.0, 0.4 + 0.12 * len(matched) + 0.25 * min(max(provider_score, 0.0), 1.0)),
            2,
        )

        if source in _SOCIAL_SOURCES:
            signal_type = "discussion"
        elif source in DIRECTORY_SOURCES:
            signal_type = "competitor"
        else:
            signal_type = "trend"

        return MarketSignal(
            id=_signal_id(source, url),
            source=source,  # type: ignore[arg-type]
            signal_type=signal_type,  # type: ignore[arg-type]
            title=title or f"{SOURCE_LABELS[source]} result for {keywords[0]}",
            summary=summary or f"Grounded result from {SOURCE_LABELS[source]} matching {', '.join(keywords[:3])}.",
            url=url,
            published_at=_parse_published_at(raw.get("published_date") or raw.get("publishedDate")),
            relevance_score=relevance,
            keywords=matched[:5],
            is_live=True,
        )

    async def _collect_source(
        self,
        source: str,
        keywords: Sequence[str],
        max_results: int,
        grounded: bool,
    ) -> Tuple[List[MarketSignal], bool, Optional[str]]:
        fallback = self._fallback_signal(source, keywords)

        if not grounded or source not in _QUERY_TEMPLATES:
            note = (
                "No search provider configured; showing a real exploration link."
                if grounded
                else "External intelligence collection is disabled; showing a real exploration link."
            )
            return [fallback], False, note

        keyword_expression = " OR ".join(f'"{keyword}"' for keyword in keywords[:3])
        query = _QUERY_TEMPLATES[source].format(kw=keyword_expression)
        raw_results = await self._search_provider(query, max_results)

        signals: List[MarketSignal] = []
        seen: set[str] = set()
        for raw in raw_results:
            signal = self._normalise_result(source, raw, keywords, fallback.url)
            if signal is None:
                continue
            key = _normalise_url(signal.url)
            if not key or key in seen:
                continue
            seen.add(key)
            signals.append(signal)
            if len(signals) >= max_results:
                break

        if not signals:
            return [fallback], False, "No grounded results returned; showing a real exploration link."

        return signals, True, None

    def _build_builder_matches(self, signals: Iterable[MarketSignal]) -> List[BuilderMatch]:
        matches: List[BuilderMatch] = []
        for signal in signals:
            if not signal.is_live or signal.source not in _SOCIAL_SOURCES:
                continue
            topic = signal.keywords[0] if signal.keywords else "your problem space"
            matches.append(
                BuilderMatch(
                    id=f"builder-{signal.id}",
                    name=f"{SOURCE_LABELS[signal.source]} discussion: {signal.title[:70]}",
                    platform=signal.source,  # type: ignore[arg-type]
                    profile_url=signal.url,
                    overlap_tags=signal.keywords[:5],
                    outreach_hook=(
                        f"Reference their post about {topic}, then share how your dossier approaches it. "
                        "Personalise the first line before sending."
                    ),
                    is_live=True,
                )
            )
            if len(matches) >= 4:
                break
        return matches

    async def collect_signals(
        self,
        keywords: Sequence[str],
        domain_persona: str,
        title: Optional[str] = None,
        max_per_source: Optional[int] = None,
    ) -> MarketIntelligenceResponse:
        """Collect, deduplicate, and score signals across all supported sources."""

        clean_keywords: List[str] = []
        for keyword in keywords:
            value = str(keyword).strip()
            if value and value.lower() not in {item.lower() for item in clean_keywords}:
                clean_keywords.append(value)
        clean_keywords = clean_keywords[:8]
        if not clean_keywords:
            clean_keywords = [domain_persona.replace("_", " ")]

        per_source = max_per_source or settings.EXTERNAL_SIGNAL_MAX_PER_SOURCE
        grounded = bool(
            settings.ENABLE_EXTERNAL_INTELLIGENCE
            and (settings.TAVILY_API_KEY or settings.EXA_API_KEY)
        )

        outcomes = await asyncio.gather(
            *(
                self._collect_source(source, clean_keywords, per_source, grounded)
                for source in SUPPORTED_SOURCES
            ),
            return_exceptions=True,
        )

        all_signals: List[MarketSignal] = []
        coverage: List[SourceCoverage] = []
        for source, outcome in zip(SUPPORTED_SOURCES, outcomes):
            if isinstance(outcome, Exception):
                logger.warning("Signal collection failed for %s: %s", source, outcome)
                signals, live, note = (
                    [self._fallback_signal(source, clean_keywords)],
                    False,
                    f"Collector error: {type(outcome).__name__}",
                )
            else:
                signals, live, note = outcome
            all_signals.extend(signals)
            coverage.append(
                SourceCoverage(
                    source=source,  # type: ignore[arg-type]
                    live=live,
                    signal_count=len(signals),
                    note=note,
                )
            )

        # Keep the highest-signal result per URL/title across all sources.
        unique: "OrderedDict[str, MarketSignal]" = OrderedDict()
        for signal in sorted(all_signals, key=lambda item: item.relevance_score, reverse=True):
            key = _normalise_url(signal.url) or signal.title.lower()
            if key not in unique:
                unique[key] = signal
        ranked_signals = list(unique.values())

        live_count = sum(1 for signal in ranked_signals if signal.is_live)
        if live_count >= 6:
            direction = "rising"
        elif live_count >= 3:
            direction = "steady"
        elif live_count > 0:
            direction = "emerging"
        else:
            direction = "unknown"

        topic = ", ".join(clean_keywords[:3])
        if live_count:
            summary = (
                f"{live_count} grounded signals across "
                f"{sum(1 for item in coverage if item.live)} platforms matched {topic}. "
                "Open a card to verify the source before acting on it."
            )
        else:
            summary = (
                f"No live search provider is configured for {topic}. These are real search links "
                "you can open to check each platform directly — no posts or metrics were invented."
            )

        return MarketIntelligenceResponse(
            generated_at=datetime.now(timezone.utc),
            title=title,
            domain_persona=domain_persona,
            keywords=clean_keywords,
            trend_direction=direction,
            trend_basis=(
                f"Heuristic from {live_count} grounded signals; not an official Google Trends metric."
            ),
            summary=summary,
            signals=ranked_signals,
            similar_builders=self._build_builder_matches(ranked_signals),
            coverage=coverage,
        )


external_intelligence = ExternalIntelligenceService()
