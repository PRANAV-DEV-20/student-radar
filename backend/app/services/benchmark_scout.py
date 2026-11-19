"""Two-tier ecosystem benchmark scout.

Tier 1 finds peer/lookalike student projects; tier 2 finds production and
research systems that solved the same hard problem at scale. Exa is the primary
grounding provider, Tavily/Exa from the shared intelligence service is the
fallback, and Gemini only organizes the results into a strict schema. No post,
startup, metric, or link is synthesized locally.
"""

import asyncio
import logging
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

import httpx

from app.core.config import settings
from app.services.external_intelligence import external_intelligence
from app.services.gemini_client import gemini_service

logger = logging.getLogger(__name__)

PEER_DOMAINS = (
    "github.com",
    "devfolio.co",
    "devpost.com",
    "ideabrowser.com",
    "reddit.com",
    "hackernews.com",
    "indiehackers.com",
)
ADVANCED_DOMAINS = (
    "arxiv.org",
    "ieeexplore.ieee.org",
    "acm.org",
    "nature.com",
    "huggingface.co",
    "github.com",
    "ycombinator.com",
    "techcrunch.com",
    "nvidia.com",
    "deepmind.google",
)


class BenchmarkScout:
    def __init__(self, client: Optional[httpx.AsyncClient] = None) -> None:
        self._client = client

    async def _search_exa(
        self,
        query: str,
        *,
        include_domains: Sequence[str],
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not settings.EXA_API_KEY:
            return []

        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(
            timeout=max(2.0, float(settings.EXTERNAL_SIGNAL_TIMEOUT_SECONDS))
        )
        payload: Dict[str, Any] = {
            "query": query,
            "numResults": 5,
            "contents": {"text": True, "summary": True},
            "includeDomains": list(include_domains),
        }
        if category:
            payload["category"] = category

        try:
            response = await client.post(
                "https://api.exa.ai/search",
                headers={
                    "x-api-key": settings.EXA_API_KEY,
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            return list(response.json().get("results") or [])
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("Exa benchmark search failed: %s", exc)
            return []
        finally:
            if owns_client:
                await client.aclose()

    @staticmethod
    def _is_candidate_url(url: str) -> bool:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return False
        path = parsed.path.lower()
        if path in {"", "/"} and not parsed.query:
            return False
        if any(token in path for token in ("/search", "/s/", "/topics/", "/tag/", "/tags/")):
            return False
        return True

    @staticmethod
    def _clean_results(raw_results: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, str]]:
        cleaned: List[Dict[str, str]] = []
        seen = set()
        for item in raw_results or []:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            if not BenchmarkScout._is_candidate_url(url) or url in seen:
                continue
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            snippet = str(
                item.get("content") or item.get("summary") or item.get("text") or ""
            ).strip()
            host = urllib.parse.urlsplit(url).netloc.replace("www.", "")
            seen.add(url)
            cleaned.append(
                {
                    "title": title[:180],
                    "url": url[:2000],
                    "snippet": snippet[:900],
                    "source": host,
                }
            )
            if len(cleaned) >= limit:
                break
        return cleaned

    @staticmethod
    def _fallback_benchmark(
        similar: List[Dict[str, str]],
        advanced: List[Dict[str, str]],
        query_basis: str,
    ) -> Dict[str, Any]:
        """Grounded fallback: copy only real result fields, no invented claims."""
        return {
            "similar_projects": [
                {
                    "name": item["title"][:160],
                    "source_platform": item["source"][:80],
                    "url": item["url"],
                    "what_they_built": item["snippet"][:600],
                    "student_differentiator": "",
                }
                for item in similar[:3]
            ],
            "advanced_upgrades": [
                {
                    "upgrade_title": item["title"][:180],
                    "inspired_by": item["source"][:180],
                    "reference_url": item["url"],
                    "architectural_impact": item["snippet"][:800],
                    "difficulty": "2-Week Milestone",
                }
                for item in advanced[:3]
            ],
            "selected_upgrades": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "query_basis": query_basis[:300],
        }

    async def build_benchmark(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Collect both tiers and synthesize a structured, URL-grounded benchmark."""
        title = str(context.get("title") or "Student project").strip()
        problem = str(context.get("problem_statement") or "").strip()
        tagline = str(context.get("tagline") or "").strip()
        stack = [str(item) for item in (context.get("tech_stack") or []) if str(item).strip()]
        persona = str(context.get("domain_persona") or "tech_builder")

        summary = (tagline or problem or title)[:260]
        core_problem = (problem or title)[:180]
        peer_query = f"open source student project OR indie prototype {summary}"[:400]
        advanced_query = (
            f"production architecture OR research breakthrough scaling {core_problem}"
        )[:400]
        query_basis = f"{peer_query} || {advanced_query}"

        async def collect_peer() -> List[Dict[str, Any]]:
            results = await self._search_exa(
                peer_query, include_domains=PEER_DOMAINS, category="github"
            )
            if not results:
                results = await external_intelligence._search_provider(
                    peer_query, 5, include_domains=PEER_DOMAINS
                )
            return results

        async def collect_advanced() -> List[Dict[str, Any]]:
            results = await self._search_exa(
                advanced_query, include_domains=ADVANCED_DOMAINS
            )
            if not results:
                results = await external_intelligence._search_provider(
                    advanced_query, 5, include_domains=ADVANCED_DOMAINS
                )
            return results

        peer_raw, advanced_raw = await asyncio.gather(
            self._safe(collect_peer()), self._safe(collect_advanced())
        )
        peer_results = self._clean_results(peer_raw)
        advanced_results = self._clean_results(advanced_raw)

        fallback = self._fallback_benchmark(peer_results, advanced_results, query_basis)
        return await gemini_service.generate_structured_benchmark(
            project_context={
                "title": title,
                "tagline": tagline,
                "problem_statement": problem,
                "tech_stack": stack,
                "domain_persona": persona,
            },
            similar_results=peer_results,
            advanced_results=advanced_results,
            fallback=fallback,
        )

    @staticmethod
    async def _safe(coro, fallback=None):
        try:
            return await coro
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("Benchmark collection step failed: %s", exc)
            return fallback if fallback is not None else []


benchmark_scout = BenchmarkScout()
