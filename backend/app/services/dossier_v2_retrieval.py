"""Stage 3 retrieval for Dossier v2.

Each research question is searched across independent sources in parallel and
time-boxed. Every returned passage carries a URL, source, quality tag and
retrieval timestamp so it can be persisted as citable evidence.
"""
from __future__ import annotations

import asyncio
import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

import httpx
from sqlalchemy import Text, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.opportunity import Opportunity
from app.models.dossier import ProjectDossier

logger = logging.getLogger(__name__)

_NEWS_DOMAINS = ("techcrunch", "theverge", "wired", "bloomberg", "reuters", "bbc", "ndtv", "timesofindia")
_FORUM_DOMAINS = ("reddit.com", "news.ycombinator.com", "indiehackers.com", "stackoverflow.com")
_OFFICIAL_DOMAINS = (".gov", ".edu", "arxiv.org", "nature.com", "who.int", "fda.gov", "europa.eu")


@dataclass
class RetrievedItem:
    url: str
    title: str
    source: str
    source_quality: str
    passage: str
    question_id: str
    canonical_key: str = ""
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        self.url = (self.url or "").strip()
        self.title = (self.title or "Untitled source")[:300]
        self.passage = (self.passage or "").strip()[:3000]
        parsed = urllib.parse.urlsplit(self.url)
        path = parsed.path.rstrip("/").lower()
        self.canonical_key = f"{parsed.netloc.lower()}{path}"[:480]


def _quality(url: str, source: str) -> str:
    lowered = f"{url} {source}".lower()
    if any(domain in lowered for domain in _FORUM_DOMAINS):
        return "forum"
    if any(domain in lowered for domain in _NEWS_DOMAINS):
        return "news"
    if any(domain in lowered for domain in _OFFICIAL_DOMAINS):
        return "official"
    if source in {"github", "huggingface", "openalex", "semantic_scholar", "pubmed", "europe_pmc"}:
        return "peer_reviewed" if source in {"openalex", "semantic_scholar", "pubmed", "europe_pmc"} else "official"
    if source == "arxiv":
        return "unknown"  # preprint: not peer reviewed
    if source == "company_blog":
        return "company"
    return "unknown"


def _keywords(text: str, limit: int = 6) -> List[str]:
    stop = {
        "this", "that", "with", "from", "what", "have", "exists", "other", "about",
        "which", "their", "there", "currently", "projects", "research", "approach",
    }
    words = [w for w in re.findall(r"[a-z0-9]{4,}", (text or "").lower()) if w not in stop]
    seen: List[str] = []
    for word in words:
        if word not in seen:
            seen.append(word)
    return seen[:limit]


class DossierRetriever:
    def __init__(self, db: AsyncSession, client: Optional[httpx.AsyncClient] = None) -> None:
        self.db = db
        self.client = client
        # One session is shared by all concurrently retrieved questions. DB
        # lookups must be serialised or SQLAlchemy tries to provision the same
        # connection twice ("concurrent operations are not permitted").
        self._db_lock = asyncio.Lock()

    async def retrieve_question(
        self,
        *,
        question: Dict[str, Any],
        dna: Dict[str, Any],
        domain_persona: str,
        mode: str,
    ) -> List[RetrievedItem]:
        queries: List[str] = list(question.get("queries") or [])[:4]
        if not queries:
            queries = [str(question.get("question") or dna.get("problem") or "student project")[:300]]
        source_types = set(question.get("source_types") or ["web", "github", "papers"])
        tasks: List[Any] = []
        if "local_corpus" in source_types:
            tasks.append(self._local_corpus(queries[0]))
        if "github" in source_types:
            tasks.append(self._github(queries[0]))
        if "papers" in source_types:
            tasks.append(self._papers(queries, domain_persona))
        if "web" in source_types:
            tasks.append(self._web(queries[:2], mode))
        if "opportunities" in source_types:
            tasks.append(self._opportunities(queries[0]))
        if "datasets" in source_types:
            tasks.append(self._datasets(queries[0]))

        owns = self.client is None
        client = self.client or httpx.AsyncClient(
            timeout=12.0,
            follow_redirects=True,
            headers={"User-Agent": "LaunchPad-Dossier-v2/1.0 (public APIs only)"},
        )
        self.client = client
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=settings.DOSSIER_V2_RETRIEVAL_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning("Retrieval timed out for %s", question.get("id"))
            results = []
        finally:
            if owns:
                await client.aclose()
                self.client = None

        items: List[RetrievedItem] = []
        for batch in results:
            if isinstance(batch, list):
                items.extend(item for item in batch if isinstance(item, RetrievedItem))
            elif isinstance(batch, Exception):
                logger.warning("Retrieval source failed for %s: %s", question.get("id"), batch)
        return self._dedupe(items, str(question.get("id") or "Q"))

    @staticmethod
    def _dedupe(items: Iterable[RetrievedItem], question_id: str) -> List[RetrievedItem]:
        seen: set[str] = set()
        accepted: List[RetrievedItem] = []
        for item in items:
            if not item.url.startswith(("http://", "https://")) or not item.passage:
                continue
            if item.canonical_key in seen:
                continue
            seen.add(item.canonical_key)
            item.question_id = question_id
            accepted.append(item)
        return accepted[:25]

    # --- sources -------------------------------------------------------------
    async def _local_corpus(self, query: str) -> List[RetrievedItem]:
        terms = _keywords(query, 4)
        if not terms:
            return []
        pattern = "%" + terms[0] + "%"
        try:
            async with self._db_lock:
                result = await self.db.execute(
                    select(ProjectDossier)
                    .where(
                        or_(
                            ProjectDossier.problem_statement.ilike(pattern),
                            ProjectDossier.title.ilike(pattern),
                            cast(ProjectDossier.tech_stack, Text).ilike(pattern),
                        )
                    )
                    .limit(5)
                )
        except Exception as exc:
            logger.warning("Local corpus search failed: %s", exc)
            return []
        return [
            RetrievedItem(
                url=f"https://studentradar.dev/p/{dossier.slug}",
                title=dossier.title,
                source="launchpad_corpus",
                source_quality="unknown",
                passage=(dossier.problem_statement or "")[:2000],
                question_id="",
            )
            for dossier in result.scalars().all()
        ]

    async def _github(self, query: str) -> List[RetrievedItem]:
        client = self.client or httpx.AsyncClient(timeout=12)
        try:
            response = await client.get(
                "https://api.github.com/search/repositories",
                params={"q": query[:180], "per_page": 5, "sort": "stars"},
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "LaunchPad-Dossier-v2/1.0",
                    **({"Authorization": f"Bearer {settings.GITHUB_TOKEN}"} if settings.GITHUB_TOKEN else {}),
                },
            )
            if response.status_code != 200:
                return []
            rows = (response.json() or {}).get("items") or []
        except Exception as exc:
            logger.warning("GitHub search failed: %s", exc)
            return []
        return [
            RetrievedItem(
                url=str(row.get("html_url") or ""),
                title=str(row.get("full_name") or "GitHub repository"),
                source="github",
                source_quality=_quality(str(row.get("html_url") or ""), "github"),
                passage=(
                    f"{row.get('description') or ''}\nTopics: {', '.join(row.get('topics') or [])} "
                    f"Stars: {row.get('stargazers_count')} Updated: {row.get('updated_at') or 'unknown'}"
                )[:2000],
                question_id="",
            )
            for row in rows[:5]
        ]

    async def _papers(self, queries: Sequence[str], persona: str) -> List[RetrievedItem]:
        query = queries[0][:200]
        tasks = [self._arxiv(query), self._openalex(query), self._semantic_scholar(query)]
        if persona == "design_biotech":
            tasks.extend([self._europe_pmc(query), self._pubmed(query)])
        results = await asyncio.gather(*tasks, return_exceptions=True)
        items: List[RetrievedItem] = []
        for batch in results:
            if isinstance(batch, list):
                items.extend(batch)
        return items

    async def _arxiv(self, query: str) -> List[RetrievedItem]:
        client = self.client or httpx.AsyncClient(timeout=12)
        try:
            response = await client.get(
                "http://export.arxiv.org/api/query",
                params={"search_query": f"all:{query}", "max_results": 4, "sortBy": "relevance"},
            )
            if response.status_code != 200:
                return []
            root = ET.fromstring(response.text)
        except Exception as exc:
            logger.warning("arXiv search failed: %s", exc)
            return []
        ns = {"a": "http://www.w3.org/2005/Atom"}
        items = []
        for entry in root.findall("a:entry", ns):
            url = (entry.findtext("a:id", "", ns) or "").strip()
            summary = " ".join((entry.findtext("a:summary", "", ns) or "").split())
            items.append(RetrievedItem(
                url=url,
                title=" ".join((entry.findtext("a:title", "", ns) or "").split()),
                source="arxiv",
                source_quality="unknown",
                passage=summary[:2500],
                question_id="",
            ))
        return items

    async def _openalex(self, query: str) -> List[RetrievedItem]:
        client = self.client or httpx.AsyncClient(timeout=12)
        try:
            response = await client.get(
                "https://api.openalex.org/works",
                params={"search": query, "per-page": 4, "mailto": "research@studentradar.dev"},
            )
            if response.status_code != 200:
                return []
            rows = (response.json() or {}).get("results") or []
        except Exception as exc:
            logger.warning("OpenAlex search failed: %s", exc)
            return []
        items = []
        for row in rows:
            url = str(row.get("doi") or row.get("id") or "")
            abstract = " ".join(
                word for idx, word in enumerate((row.get("abstract_inverted_index") or {}).get("_", [])[:80])
                for word in [word]
            )
            if isinstance(row.get("abstract_inverted_index"), dict):
                positions: Dict[int, str] = {}
                for word, idxs in row["abstract_inverted_index"].items():
                    for idx in idxs[:3]:
                        positions[int(idx)] = word
                abstract = " ".join(positions[key] for key in sorted(positions)[:200])
            items.append(RetrievedItem(
                url=url,
                title=str(row.get("title") or "OpenAlex work"),
                source="openalex",
                source_quality="peer_reviewed" if row.get("primary_location") else "unknown",
                passage=abstract[:2500] or str(row.get("publication_year") or ""),
                question_id="",
            ))
        return items

    async def _semantic_scholar(self, query: str) -> List[RetrievedItem]:
        client = self.client or httpx.AsyncClient(timeout=12)
        try:
            response = await client.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={"query": query, "limit": 4, "fields": "title,abstract,url,year,venue,externalIds"},
            )
            if response.status_code != 200:
                return []
            rows = (response.json() or {}).get("data") or []
        except Exception as exc:
            logger.warning("Semantic Scholar search failed: %s", exc)
            return []
        return [
            RetrievedItem(
                url=str(row.get("url") or (row.get("externalIds") or {}).get("DOI") or ""),
                title=str(row.get("title") or "Paper"),
                source="semantic_scholar",
                source_quality="peer_reviewed" if row.get("venue") else "unknown",
                passage=(row.get("abstract") or f"Published {row.get('year') or 'unknown'}")[:2500],
                question_id="",
            )
            for row in rows
        ]

    async def _europe_pmc(self, query: str) -> List[RetrievedItem]:
        client = self.client or httpx.AsyncClient(timeout=12)
        try:
            response = await client.get(
                "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                params={"query": query, "format": "json", "pageSize": 4},
            )
            if response.status_code != 200:
                return []
            rows = (((response.json() or {}).get("resultList") or {}).get("result") or [])
        except Exception as exc:
            logger.warning("Europe PMC search failed: %s", exc)
            return []
        return [
            RetrievedItem(
                url=f"https://europepmc.org/article/{row.get('source', 'MED')}/{row.get('id', '')}",
                title=str(row.get("title") or "Europe PMC record"),
                source="europe_pmc",
                source_quality="peer_reviewed",
                passage=(row.get("abstractText") or "")[:2500],
                question_id="",
            )
            for row in rows
        ]

    async def _pubmed(self, query: str) -> List[RetrievedItem]:
        client = self.client or httpx.AsyncClient(timeout=12)
        try:
            response = await client.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                params={"db": "pubmed", "term": query, "retmode": "json", "retmax": 4},
            )
            if response.status_code != 200:
                return []
            ids = ((response.json() or {}).get("esearchresult") or {}).get("idlist") or []
        except Exception as exc:
            logger.warning("PubMed search failed: %s", exc)
            return []
        return [
            RetrievedItem(
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                title=f"PubMed record {pmid}",
                source="pubmed",
                source_quality="peer_reviewed",
                passage=f"PubMed indexed record {pmid} matching the research question.",
                question_id="",
            )
            for pmid in ids[:4]
        ]

    async def _web(self, queries: Sequence[str], mode: str) -> List[RetrievedItem]:
        if not settings.TAVILY_API_KEY:
            return []
        client = self.client or httpx.AsyncClient(timeout=12)
        items: List[RetrievedItem] = []
        for query in queries[:2]:
            try:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": settings.TAVILY_API_KEY,
                        "query": query[:300],
                        "search_depth": "advanced" if mode == "deep" else "basic",
                        "max_results": 5,
                        "include_answer": False,
                    },
                )
                if response.status_code != 200:
                    continue
                rows = (response.json() or {}).get("results") or []
            except Exception as exc:
                logger.warning("Tavily search failed: %s", exc)
                continue
            for row in rows[:5]:
                url = str(row.get("url") or "")
                content = str(row.get("content") or row.get("snippet") or "")
                items.append(RetrievedItem(
                    url=url,
                    title=str(row.get("title") or url),
                    source="web",
                    source_quality=_quality(url, "web"),
                    passage=content[:2500],
                    question_id="",
                ))
        return items

    async def _opportunities(self, query: str) -> List[RetrievedItem]:
        term = (_keywords(query, 1) or ["hackathon"])[0]
        pattern = f"%{term}%"
        try:
            async with self._db_lock:
                result = await self.db.execute(
                    select(Opportunity).where(
                        or_(Opportunity.title.ilike(pattern), Opportunity.description.ilike(pattern))
                    ).limit(5)
                )
        except Exception as exc:
            logger.warning("Opportunity lookup failed: %s", exc)
            return []
        return [
            RetrievedItem(
                url=str(row.canonical_source_url or "https://studentradar.dev/radar"),
                title=str(row.title or "Opportunity"),
                source="launchpad_radar",
                source_quality="official" if (row.decision_metadata or {}).get("is_live") else "unknown",
                passage=(str(row.description or "") + f" Deadline: {row.deadline}")[:2000],
                question_id="",
            )
            for row in result.scalars().all()
        ]

    async def _datasets(self, query: str) -> List[RetrievedItem]:
        client = self.client or httpx.AsyncClient(timeout=12)
        try:
            response = await client.get(
                "https://huggingface.co/api/datasets",
                params={"search": _keywords(query, 2)[0] if _keywords(query, 2) else query[:40], "limit": 4},
            )
            if response.status_code != 200:
                return []
            rows = response.json() or []
        except Exception as exc:
            logger.warning("Hugging Face dataset search failed: %s", exc)
            return []
        return [
            RetrievedItem(
                url=f"https://huggingface.co/datasets/{row.get('id')}",
                title=str(row.get("id") or "Dataset"),
                source="huggingface",
                source_quality="official",
                passage=(
                    f"Hugging Face dataset {row.get('id')}. Downloads: {row.get('downloads', 'unknown')}. "
                    f"Tags: {', '.join((row.get('tags') or [])[:8])}"
                )[:1500],
                question_id="",
            )
            for row in rows[:4]
        ]
