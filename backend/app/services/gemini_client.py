import asyncio
import hashlib
import json
import logging
import math
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# The model fills the slots; the templates stay deterministic so every Radar
# tab keeps its required query shape and domain allowlist.
RADAR_QUERY_TEMPLATES: Dict[str, str] = {
    "hackathons": "{domain} hackathon OR buildathon registration open 2026",
    "news": "{core_problem_or_tech} launch OR release OR funding",
    "builders": "building {problem_statement} OR looking for {solution_type}",
}


class GeminiService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.client = None
        self._auth_failed = False
        if self.api_key and self.api_key != "your_gemini_api_key_here":
            try:
                from google import genai

                self.client = genai.Client(api_key=self.api_key)
                logger.info("Google Gemini SDK initialized successfully.")
            except Exception as exc:  # pragma: no cover - depends on optional package
                logger.warning(f"Failed to initialize google-genai client: {exc}. Falling back to deterministic synthesis.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def generate_structured_dossier(
        self,
        raw_content: str,
        domain_persona: str,
        input_type: str = "idea",
    ) -> Dict[str, Any]:
        """Extract a publication-grade dossier using Gemini structured output."""
        fallback = self._fallback_dossier_synthesis(raw_content, domain_persona, input_type)

        system_instruction = (
            "You are an expert technical venture evaluator and research synthesizer. "
            f"Analyze the provided student project for the domain persona '{domain_persona}'. "
            "Output a strictly structured JSON object matching the Proof-of-Work Dossier schema: "
            "title, tagline, stage ('Idea'|'Prototype'|'MVP'|'Research'), problem_statement, "
            "solution_breakdown (architecture, core_algorithms, hardware_or_infra), "
            "tech_stack (list of 4-7 exact tools/languages), key_metrics (list of {label, value}), "
            "whitespace_analysis ({market_gap, top_voices}), missing_roles (list of {role, reason}). "
            "Never invent benchmarks or metrics that are not supported by the input."
        )

        if self.client:
            try:
                prompt = f"Input Type: {input_type}\nContent:\n{raw_content[:8000]}"
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=settings.GEMINI_TEXT_MODEL,
                    contents=[system_instruction, prompt],
                    config={"response_mime_type": "application/json"},
                )
                parsed = self._parse_json_payload(getattr(response, "text", None))
                if isinstance(parsed, dict) and parsed:
                    return self._normalize_dossier(parsed, fallback)
            except Exception as exc:  # pragma: no cover - network dependent
                logger.warning(f"Gemini API call failed, falling back to heuristic engine: {exc}")

        return fallback

    async def generate_structured_benchmark(
        self,
        *,
        project_context: Dict[str, Any],
        similar_results: List[Dict[str, Any]],
        advanced_results: List[Dict[str, Any]],
        fallback: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Synthesize the two-tier benchmark with URL-grounded structured output.

        The model may only organize and explain the supplied search results; it
        cannot introduce a link that was not returned by Exa. This keeps the
        mentor panel honest even when the upstream model is unavailable.
        """
        if not similar_results and not advanced_results:
            return fallback

        system_instruction = (
            "You are a technical product mentor for student engineers. "
            "Using ONLY the supplied search results, produce a strict JSON object with keys: "
            "similar_projects (max 3 objects: name, source_platform, url, what_they_built, "
            "student_differentiator), advanced_upgrades (max 3 objects: upgrade_title, "
            "inspired_by, reference_url, architectural_impact, difficulty). "
            "Every url/reference_url must be copied verbatim from the supplied results. "
            "Never invent a project, startup, paper, metric, star count, funding figure, or link. "
            "student_differentiator must be an honest comparison grounded in the project context; "
            "leave it empty when you cannot support a comparison. "
            "difficulty must be either 'Weekend Sprint' or '2-Week Milestone'."
        )
        prompt = (
            f"PROJECT CONTEXT:\n{json.dumps(project_context, default=str, ensure_ascii=False)[:4000]}\n\n"
            f"PEER/LOOKALIKE RESULTS:\n{json.dumps(similar_results, default=str, ensure_ascii=False)[:8000]}\n\n"
            f"PRODUCTION/RESEARCH RESULTS:\n{json.dumps(advanced_results, default=str, ensure_ascii=False)[:8000]}"
        )

        if self.client:
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=settings.GEMINI_TEXT_MODEL,
                    contents=[system_instruction, prompt],
                    config={"response_mime_type": "application/json"},
                )
                parsed = self._parse_json_payload(getattr(response, "text", None))
                if isinstance(parsed, dict) and parsed:
                    return self._normalize_benchmark(
                        parsed,
                        fallback,
                        allowed_similar={str(item.get("url") or "") for item in similar_results},
                        allowed_advanced={str(item.get("url") or "") for item in advanced_results},
                    )
            except Exception as exc:  # pragma: no cover - network dependent
                logger.warning("Gemini benchmark synthesis failed: %s", exc)

        return fallback

    async def generate_pr_copy(
        self,
        dossier_data: Dict[str, Any],
        playbook_markdown: str,
        tone: str = "high_octane",
        target_audience: str = "Engineers & Investors",
    ) -> Dict[str, Any]:
        """Synthesize high-conversion PR copy from playbooks and dossier data."""
        fallback = self._fallback_pr_synthesis(dossier_data, tone)

        if self.client:
            try:
                prompt = (
                    f"PLAYBOOK RULES:\n{playbook_markdown}\n\n"
                    f"PROJECT DOSSIER DATA:\n{json.dumps(dossier_data, indent=2, default=str)}\n\n"
                    f"TONE: {tone}\nAUDIENCE: {target_audience}\n\n"
                    "Generate a JSON object with: headline (str), body_markdown (str), "
                    "hooks (list of str), suggested_tags (list of str). "
                    "If benchmark_analysis.selected_upgrades is present, add a "
                    "'Building in Public — Version 2.0 Roadmap' section naming those "
                    "upgrades and citing their reference_url values. Do not invent "
                    "metrics, funding, or links. Follow the playbook constraints exactly."
                )
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=settings.GEMINI_TEXT_MODEL,
                    contents=[prompt],
                    config={"response_mime_type": "application/json"},
                )
                parsed = self._parse_json_payload(getattr(response, "text", None))
                if isinstance(parsed, dict) and parsed:
                    return self._normalize_pr_payload(parsed, fallback)
            except Exception as exc:  # pragma: no cover - network dependent
                logger.warning(f"Gemini PR generation failed: {exc}")

        return fallback

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate a 768-dimensional text embedding (with deterministic fallback)."""
        if self.client and text.strip():
            try:
                result = await asyncio.to_thread(
                    self.client.models.embed_content,
                    model=settings.GEMINI_EMBEDDING_MODEL,
                    contents=text[:2000],
                )
                vector = self._extract_embedding(result)
                if vector:
                    return self._normalize_embedding(vector)
            except Exception as exc:  # pragma: no cover - network dependent
                logger.warning(f"Embedding generation failed: {exc}")

        return self._fallback_embedding(text)

    async def generate_chat_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate plain text for the OpenAI-compatible /v1 surface.

        Any requested OpenAI model name is accepted but mapped onto the
        configured Gemini text model, so OpenAI-style clients can talk to this
        API without a 404/400 loop. Falls back to a deterministic answer when
        no Gemini key is configured.
        """
        if self.client:
            try:
                config: Dict[str, Any] = {}
                if temperature is not None:
                    config["temperature"] = temperature
                if max_tokens is not None:
                    config["max_output_tokens"] = max_tokens
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=model or settings.GEMINI_TEXT_MODEL,
                    contents=prompt,
                    config=config or None,
                )
                text = getattr(response, "text", None)
                if isinstance(text, str) and text.strip():
                    return text.strip()
            except Exception as exc:  # pragma: no cover - network dependent
                logger.warning(f"Gemini chat completion failed: {exc}")

        return (
            "Student Radar API is reachable, but no live language model is "
            "configured. Set GEMINI_API_KEY to enable generations. This "
            "response is served by the deterministic OpenAI-compatible "
            "fallback at /v1/chat/completions."
        )

    async def _generate_json_prompt(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Single JSON generation call shared by query planning and reranking."""

        if self._auth_failed or not self.api_key or self.api_key == "your_gemini_api_key_here":
            return None

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_TEXT_MODEL}:generateContent"
        )
        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                # Send the credential as a header so it never appears in
                # httpx access logs or proxy URLs.
                response = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": self.api_key,
                    },
                )
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network dependent
            if exc.response.status_code in {401, 403}:
                if not self._auth_failed:
                    logger.warning(
                        "Gemini API key was rejected; using deterministic Radar "
                        "fallbacks until the service restarts."
                    )
                self._auth_failed = True
            else:
                logger.warning("Gemini JSON generation failed: %s", exc)
            return None
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("Gemini JSON generation failed: %s", exc)
            return None

        for candidate in body.get("candidates") or []:
            parts = ((candidate.get("content") or {}).get("parts") or [])
            for part in parts:
                parsed = self._parse_json_payload(part.get("text"))
                if parsed:
                    return parsed
        return None

    async def generate_radar_queries(
        self,
        context: Dict[str, Any],
        language: str = "en",
    ) -> Dict[str, str]:
        """Turn a project dossier into one precise query per Radar intent.

        Gemini fills only the fuzzy slots (domain, problem, solution type). The
        final query strings are assembled locally from fixed templates so the
        model cannot swap in a broad keyword-stuffed query.
        """

        slots = self._radar_query_slots(context)
        prompt = (
            "You are a search planner for a student opportunity radar. "
            f"Respond in {language}. Return JSON only with exactly these keys: "
            "domain, core_problem_or_tech, problem_statement, solution_type.\n"
            "Rules: use the project's actual problem, not a stack list; keep "
            "each value under 90 characters; do not invent metrics, deadlines, "
            "or product claims.\n\n"
            f"PROJECT CONTEXT:\n{json.dumps(context, default=str, ensure_ascii=False)}"
        )
        parsed = await self._generate_json_prompt(prompt)
        if parsed:
            for key in tuple(slots):
                value = parsed.get(key)
                if isinstance(value, str) and value.strip():
                    slots[key] = value.strip()[:90]

        return {
            intent: template.format(**slots)
            for intent, template in RADAR_QUERY_TEMPLATES.items()
        }

    @staticmethod
    def _trim_slot(value: str, limit: int = 90) -> str:
        value = (value or "").strip()
        if len(value) <= limit:
            return value
        clipped = value[:limit]
        boundary = max(clipped.rfind(" "), clipped.rfind(","))
        return (clipped[:boundary] if boundary >= limit // 2 else clipped).rstrip(" ,;")

    @classmethod
    def _radar_query_slots(cls, context: Dict[str, Any]) -> Dict[str, str]:
        problem = str(context.get("problem_statement") or context.get("raw_idea") or "").strip()
        title = str(context.get("title") or "").strip()
        domain = str(context.get("domain") or context.get("persona_label") or "").strip()
        solution = str(
            context.get("solution_type")
            or context.get("tagline")
            or context.get("stage")
            or ""
        ).strip()
        tech = ", ".join(str(item) for item in (context.get("tech_stack") or [])[:3])

        return {
            "domain": cls._trim_slot(domain or title or "student builders"),
            "core_problem_or_tech": cls._trim_slot(problem or tech or domain or "student project"),
            "problem_statement": cls._trim_slot(problem or title or domain or "student project problem"),
            "solution_type": cls._trim_slot(solution or tech or "practical solution"),
        }

    async def rerank_radar_results(
        self,
        items: List[Dict[str, Any]],
        project_summary: str,
        intent: str,
        *,
        search_query: str = "",
        language: str = "en",
        threshold: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Batch-score raw search hits and drop low-relevance / wrong-language rows.

        A deterministic overlap score is used when Gemini is unavailable, so
        the pipeline never silently promotes unverified generic pages.
        """

        if not items:
            return []

        cutoff = settings.RADAR_RERANK_THRESHOLD if threshold is None else threshold
        payload_items = [
            {
                "id": str(item.get("id") or index),
                "title": str(item.get("title") or "")[:300],
                "snippet": str(item.get("summary") or item.get("snippet") or "")[:700],
                "url": str(item.get("url") or "")[:500],
                "published_date": str(item.get("published_at") or item.get("published_date") or ""),
            }
            for index, item in enumerate(items)
        ]
        prompt = (
            "You are a relevance judge for a student opportunity radar. "
            f"Requested language: {language}. Radar intent: {intent}. "
            f"Project summary: {project_summary[:1500]}\n\n"
            "Score every result 0-100 for genuine semantic fit with the project's "
            "problem (not shared technology words). A result about an unrelated "
            "audience, a generic homepage, or an old evergreen thread must score "
            "below 50. Return JSON only: {\"results\": [{\"id\": \"...\", "
            "\"score\": 0, \"language\": \"en\", \"reason\": \"short\", "
            "\"published_at\": \"ISO date or empty\", "
            "\"deadline\": \"ISO date or empty\"}]}. "
            "Use an empty string for any date not explicitly stated in the result. "
            "Do not invent dates. Include one entry per input id."
            f"\n\nRESULTS:\n{json.dumps(payload_items, ensure_ascii=False)}"
        )
        parsed = await self._generate_json_prompt(prompt)

        scores: Dict[str, Dict[str, Any]] = {}
        if parsed:
            raw_scores = parsed.get("results") if isinstance(parsed, dict) else parsed
            if isinstance(raw_scores, list):
                for entry in raw_scores:
                    if isinstance(entry, dict) and entry.get("id") is not None:
                        scores[str(entry["id"])] = entry

        accepted: List[Dict[str, Any]] = []
        for index, item in enumerate(items):
            item_id = str(item.get("id") or index)
            verdict = scores.get(item_id)
            if verdict is None:
                # When the model omits an item, apply the conservative local
                # score instead of silently keeping unverified noise.
                score, reason, language_code = self._heuristic_radar_score(
                    item, project_summary, search_query
                )
            else:
                try:
                    score = max(0, min(100, int(round(float(verdict.get("score", 0))))))
                except (TypeError, ValueError):
                    score = 0
                reason = str(verdict.get("reason") or "")[:240]
                language_code = str(verdict.get("language") or item.get("language") or "").lower()

            if score < cutoff:
                continue
            if language and language_code and not self._language_matches(language, language_code):
                continue

            enriched = dict(item)
            enriched["relevance_score_100"] = score
            enriched["rerank_reason"] = reason
            enriched["language"] = language_code or language

            if verdict:
                published = self._coerce_datetime(verdict.get("published_at"))
                deadline = self._coerce_datetime(verdict.get("deadline"))
                if published:
                    enriched["published_at"] = published
                if deadline:
                    enriched["deadline"] = deadline
                    enriched["deadline_explicit"] = True

            accepted.append(enriched)

        accepted.sort(key=lambda entry: entry["relevance_score_100"], reverse=True)
        return accepted

    @staticmethod
    def _heuristic_radar_score(
        item: Dict[str, Any],
        project_summary: str,
        search_query: str = "",
    ) -> Tuple[int, str, str]:
        haystack = f"{item.get('title', '')} {item.get('summary') or item.get('snippet') or ''}".lower()
        reference = f"{project_summary} {search_query}".lower()
        stopwords = {
            "a", "an", "and", "for", "from", "in", "of", "on", "or", "the", "to",
            "with", "open", "registration", "launch", "release", "funding",
        }
        terms = {
            term for term in re.findall(r"[a-z0-9]{4,}", reference) if term not in stopwords
        }
        if not terms:
            return 0, "No project context available.", ""
        overlap = len([term for term in terms if term in haystack])
        score = min(100, round(35 + (65 * overlap / max(2, min(len(terms), 8)))))
        return score, "Local lexical overlap fallback.", str(item.get("language") or "").lower()

    @staticmethod
    def _language_matches(requested: str, detected: str) -> bool:
        wanted = requested.strip().lower().split("-")[0]
        found = detected.strip().lower().split("-")[0]
        if not found:
            return True
        return found == wanted

    @staticmethod
    def _coerce_datetime(value: Any) -> Optional[datetime]:
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

    async def search_grounded_events(self, query: str, persona: str) -> List[Dict[str, Any]]:
        """Discover real events with Gemini Search Grounding.

        The model is used only to extract structured facts from grounded web
        results. A result is accepted only when its ``source_url`` is present in
        the response's grounding citations, so the model cannot invent an
        event, organiser, deadline, or reward out of thin air.
        """

        if self._auth_failed or not self.api_key or self.api_key == "your_gemini_api_key_here":
            return []

        prompt = (
            "Find currently open student opportunities (hackathons, grants, "
            f"fellowships, build sprints, or conferences) for the persona '{persona}'.\n"
            f"Search query: {query}\n\n"
            "Return JSON only, shaped as {\"events\": [...]}. Each event must use "
            "only facts that appear in the grounded sources and must include:\n"
            "- title\n"
            "- source_url (the exact URL from the grounded source)\n"
            "- summary (short, factual)\n"
            "- deadline (ISO date or datetime, only if explicitly stated)\n"
            "- host_organization (optional; omit when unknown)\n"
            "- location_type ('virtual', 'in_person', or 'hybrid'; omit when unknown)\n"
            "- city (optional)\n"
            "- reward_pool (optional; omit when not explicitly stated)\n"
            "- tags (array of short strings)\n\n"
            "Do not guess URLs, deadlines, rewards, or organiser names. If a "
            "detail is missing, omit it. Do not include an event without a "
            "source_url taken directly from the grounded sources."
        )

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_TEXT_MODEL}:generateContent"
        )
        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {"responseMimeType": "application/json"},
        }

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                # Send the credential as a header so it never appears in
                # httpx access logs or proxy URLs.
                response = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": self.api_key,
                    },
                )
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network dependent
            if exc.response.status_code in {401, 403}:
                if not self._auth_failed:
                    logger.warning(
                        "Gemini API key was rejected; using deterministic Radar "
                        "fallbacks until the service restarts."
                    )
                self._auth_failed = True
            else:
                logger.warning("Gemini grounded event search failed: %s", exc)
            return []
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("Gemini grounded event search failed: %s", exc)
            return []

        grounded_urls: List[str] = []
        parsed_events: List[Dict[str, Any]] = []
        for candidate in body.get("candidates") or []:
            metadata = (
                candidate.get("groundingMetadata")
                or candidate.get("grounding_metadata")
                or {}
            )
            for chunk in metadata.get("groundingChunks") or []:
                web = chunk.get("web") or {}
                uri = str(web.get("uri") or "").strip()
                if uri.startswith(("http://", "https://")):
                    grounded_urls.append(uri)

            parts = ((candidate.get("content") or {}).get("parts") or [])
            for part in parts:
                parsed = self._parse_json_payload(part.get("text"))
                if not parsed:
                    continue
                events = parsed.get("events") if isinstance(parsed, dict) else parsed
                if isinstance(events, list):
                    parsed_events.extend(
                        item for item in events if isinstance(item, dict)
                    )

        accepted: List[Dict[str, Any]] = []
        canonical_urls = {url.rstrip("/") for url in grounded_urls}
        for item in parsed_events:
            source_url = str(item.get("source_url") or item.get("url") or "").strip()
            if not source_url or source_url.rstrip("/") not in canonical_urls:
                continue

            title = str(item.get("title") or "").strip()
            if not title:
                continue

            deadline = self._parse_event_deadline(item.get("deadline"))
            if deadline is None:
                # A deadline is required for the radar ranking. Never invent one.
                continue

            accepted.append(
                {
                    "title": title[:250],
                    "category": self._infer_event_category(title, item),
                    "canonical_source_url": source_url,
                    "host_organization": str(item.get("host_organization") or "").strip()[:150] or None,
                    "deadline": deadline,
                    "description": str(item.get("summary") or title).strip()[:4000],
                    "tags": self._string_list(item.get("tags"), limit=6),
                    "location_type": str(item.get("location_type") or "virtual").strip()[:50],
                    "city": str(item.get("city") or "").strip()[:100] or None,
                    "reward_pool": str(item.get("reward_pool") or "").strip()[:100] or None,
                    "decision_metadata": {
                        "source": "gemini_search_grounding",
                        "is_live": True,
                        "persona": persona,
                        "grounding_urls": grounded_urls[:8],
                    },
                }
            )

        return accepted

    @staticmethod
    def _parse_event_deadline(value: Any) -> Optional[datetime]:
        if not isinstance(value, str) or not value.strip():
            return None
        raw = value.strip()
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed = datetime.strptime(raw[:10], "%Y-%m-%d")
            except ValueError:
                return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        if parsed <= datetime.now(timezone.utc):
            return None
        return parsed

    @staticmethod
    def _infer_event_category(title: str, item: Dict[str, Any]) -> str:
        explicit = str(item.get("category") or "").strip().lower()
        if explicit in {"hackathon", "grant", "fellowship", "build_sprint", "conference"}:
            return explicit
        blob = f"{title} {item.get('summary', '')}".lower()
        if any(word in blob for word in ("hackathon", "build sprint", "buildathon", "hack")):
            return "hackathon"
        if any(word in blob for word in ("grant", "funding", "prize")):
            return "grant"
        if any(word in blob for word in ("fellowship", "residency")):
            return "fellowship"
        return "general_event"

    # ------------------------------------------------------------------
    # Response normalization
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_json_payload(text: Optional[str]) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end <= start:
                return None
            try:
                value = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
        return value if isinstance(value, dict) else None

    @staticmethod
    def _string_list(value: Any, limit: int = 12) -> List[str]:
        if isinstance(value, str):
            value = [part.strip() for part in re.split(r"[,;\n]", value)]
        if not isinstance(value, (list, tuple)):
            return []
        return [str(item).strip() for item in value if str(item).strip()][:limit]

    def _normalize_dossier(self, data: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(fallback)

        for key, max_len in (("title", 200), ("tagline", 300), ("problem_statement", 8000)):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                normalized[key] = value.strip()[:max_len]

        stage = data.get("stage")
        if isinstance(stage, str) and stage.strip():
            normalized["stage"] = stage.strip()[:40]
        normalized.setdefault("stage", fallback.get("stage", "Prototype"))

        breakdown = data.get("solution_breakdown")
        if isinstance(breakdown, dict) and breakdown:
            normalized["solution_breakdown"] = {
                str(key): value if isinstance(value, (str, int, float, list, dict)) else str(value)
                for key, value in breakdown.items()
            }
        elif isinstance(breakdown, str) and breakdown.strip():
            normalized["solution_breakdown"] = {"architecture": breakdown.strip()}

        tech_stack = self._string_list(data.get("tech_stack"))
        if tech_stack:
            normalized["tech_stack"] = tech_stack

        metrics = data.get("key_metrics")
        if isinstance(metrics, list):
            normalized_metrics = []
            for metric in metrics[:8]:
                if isinstance(metric, dict) and metric.get("label") and metric.get("value") is not None:
                    normalized_metrics.append(
                        {"label": str(metric["label"])[:80], "value": str(metric["value"])[:80]}
                    )
            if normalized_metrics:
                normalized["key_metrics"] = normalized_metrics

        whitespace = data.get("whitespace_analysis")
        if isinstance(whitespace, dict) and (whitespace.get("market_gap") or whitespace.get("top_voices")):
            normalized["whitespace_analysis"] = {
                "market_gap": str(whitespace.get("market_gap") or fallback["whitespace_analysis"]["market_gap"])[:2000],
                "top_voices": self._string_list(
                    whitespace.get("top_voices") or fallback["whitespace_analysis"].get("top_voices", []),
                    limit=6,
                ),
            }

        roles = data.get("missing_roles")
        if isinstance(roles, list):
            normalized_roles = []
            for role in roles[:8]:
                if isinstance(role, dict) and role.get("role"):
                    normalized_roles.append(
                        {
                            "role": str(role["role"])[:120],
                            "reason": str(role.get("reason", ""))[:500],
                        }
                    )
            if normalized_roles:
                normalized["missing_roles"] = normalized_roles

        return normalized

    @staticmethod
    def _normalize_benchmark(
        data: Dict[str, Any],
        fallback: Dict[str, Any],
        *,
        allowed_similar: Optional[set] = None,
        allowed_advanced: Optional[set] = None,
    ) -> Dict[str, Any]:
        """Clamp model output and reject any URL outside the supplied results."""
        normalized = dict(fallback)

        similar = data.get("similar_projects")
        if isinstance(similar, list):
            kept = []
            for item in similar[:3]:
                if not isinstance(item, dict):
                    continue
                url = str(item.get("url") or "").strip()
                if allowed_similar is not None and url not in allowed_similar:
                    continue
                if not url.startswith(("http://", "https://")):
                    continue
                name = str(item.get("name") or "").strip()
                if not name:
                    continue
                kept.append(
                    {
                        "name": name[:160],
                        "source_platform": str(item.get("source_platform") or "Web source")[:80],
                        "url": url[:2000],
                        "what_they_built": str(item.get("what_they_built") or "")[:600],
                        "student_differentiator": str(item.get("student_differentiator") or "")[:600],
                    }
                )
            if kept:
                normalized["similar_projects"] = kept

        advanced = data.get("advanced_upgrades")
        if isinstance(advanced, list):
            kept = []
            for item in advanced[:3]:
                if not isinstance(item, dict):
                    continue
                url = str(item.get("reference_url") or "").strip()
                if allowed_advanced is not None and url not in allowed_advanced:
                    continue
                if not url.startswith(("http://", "https://")):
                    continue
                title = str(item.get("upgrade_title") or "").strip()
                if not title:
                    continue
                difficulty = str(item.get("difficulty") or "").strip()
                if difficulty not in {"Weekend Sprint", "2-Week Milestone"}:
                    difficulty = "2-Week Milestone"
                kept.append(
                    {
                        "upgrade_title": title[:180],
                        "inspired_by": str(item.get("inspired_by") or "Production source")[:180],
                        "reference_url": url[:2000],
                        "architectural_impact": str(item.get("architectural_impact") or "")[:800],
                        "difficulty": difficulty,
                    }
                )
            if kept:
                normalized["advanced_upgrades"] = kept

        return normalized

    def _normalize_pr_payload(self, data: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(fallback)
        for key in ("headline", "body_markdown"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                normalized[key] = value.strip()
        for key in ("hooks", "suggested_tags"):
            values = self._string_list(data.get(key), limit=8)
            if values:
                normalized[key] = values
        return normalized

    def _extract_embedding(self, result: Any) -> List[float]:
        embeddings = getattr(result, "embeddings", None)
        if embeddings:
            first = embeddings[0]
            values = getattr(first, "values", None)
            if values is None and isinstance(first, dict):
                values = first.get("values")
            if values is not None:
                return [float(value) for value in values]

        embedding = getattr(result, "embedding", None)
        if embedding is not None:
            values = getattr(embedding, "values", embedding if isinstance(embedding, list) else None)
            if values is not None:
                return [float(value) for value in values]
        return []

    @staticmethod
    def _normalize_embedding(vector: List[float]) -> List[float]:
        dims = settings.GEMINI_EMBEDDING_DIMENSIONS
        values = [float(value) for value in vector[:dims]]
        if len(values) < dims:
            values.extend([0.0] * (dims - len(values)))
        norm = math.sqrt(sum(value * value for value in values))
        if norm == 0.0:
            return GeminiService._fallback_embedding(str(values))
        return [round(value / norm, 6) for value in values]

    @staticmethod
    def _fallback_embedding(text: str) -> List[float]:
        dims = settings.GEMINI_EMBEDDING_DIMENSIONS
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
        vector = [math.sin(seed + index * 0.1) for index in range(dims)]
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [round(value / norm, 6) for value in vector]

    # ------------------------------------------------------------------
    # Deterministic fallbacks
    # ------------------------------------------------------------------
    @staticmethod
    def _base_name(raw_content: str) -> str:
        lines = [line.strip() for line in (raw_content or "").splitlines() if line.strip()]
        candidate = lines[0] if lines else "Project Dossier"

        markdown_link = re.search(r"\[([^\]]+)\]\([^)]+\)", candidate)
        if markdown_link:
            candidate = markdown_link.group(1)
        elif re.search(r"https?://", candidate):
            parsed = urllib.parse.urlsplit(candidate.split()[0])
            candidate = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1]) or parsed.netloc

        candidate = re.sub(r"[_\-]+", " ", candidate)
        return candidate.strip().title()[:60] or "Project Dossier"

    def _fallback_dossier_synthesis(
        self,
        raw_content: str,
        domain_persona: str,
        input_type: str,
    ) -> Dict[str, Any]:
        """Build a dossier grounded in the submitted text.

        The old fallback returned a fixed demo project, which made every
        concept look identical and silently ignored the student's input. The
        heuristic synthesizer extracts the title, problem, stack, metrics, and
        roles from the actual artifact instead.
        """
        from app.services.heuristic_synthesis import synthesize_dossier

        return synthesize_dossier(
            raw_content=raw_content,
            domain_persona=domain_persona,
            input_type=input_type,
        )

    def _fallback_pr_synthesis(self, dossier: Dict[str, Any], tone: str) -> Dict[str, Any]:
        title = dossier.get("title", "Open Source Breakthrough")
        tagline = dossier.get("tagline", "High-impact technical architecture.")
        metrics = dossier.get("key_metrics", [])
        metric_str = (
            ", ".join(f"{metric.get('label')}: {metric.get('value')}" for metric in metrics[:2])
            if metrics
            else ""
        )
        headline = (
            f"Why we built {title} — and what the submitted dossier actually says."
        )
        performance_line = f"• Verified metrics: {metric_str}\n" if metric_str else ""

        benchmark = dossier.get("benchmark_analysis") or {}
        selected = (benchmark.get("selected_upgrades") or []) if isinstance(benchmark, dict) else []
        roadmap_lines = []
        for upgrade in selected[:3]:
            if not isinstance(upgrade, dict) or not upgrade.get("upgrade_title"):
                continue
            line = f"• {upgrade['upgrade_title']}"
            if upgrade.get("reference_url"):
                line += f" — {upgrade['reference_url']}"
            roadmap_lines.append(line)
        roadmap_section = (
            "Building in Public — Version 2.0 Roadmap:\n" + "\n".join(roadmap_lines) + "\n\n"
            if roadmap_lines
            else ""
        )

        body = (
            "This proof-of-work dossier is grounded in the submitted artifact rather than a "
            "template.\n\n"
            f"Over the last few months, we tackled this head-on: {tagline}\n\n"
            "Key Architectural Highlights:\n"
            f"• Core Problem: {dossier.get('problem_statement', '')}\n"
            f"• Stack: {', '.join(dossier.get('tech_stack') or [])}\n"
            f"{performance_line}\n"
            f"{roadmap_section}"
            "Full Proof-of-Work Dossier and architecture blueprint is now open to explore. "
            "Would love thoughts from engineers and researchers working on similar problems!"
        )
        return {
            "headline": headline,
            "body_markdown": body,
            "hooks": [
                f"We built {title}: here is architecture behind it.",
                f"How {title} approached {str(dossier.get('problem_statement', ''))[:60]}...",
            ],
            "suggested_tags": ["#Engineering", "#OpenSource", "#Innovation", "#TechBuilders"],
        }


gemini_service = GeminiService()
