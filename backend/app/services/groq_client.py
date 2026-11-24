"""Small OpenAI-compatible Groq client for structured JSON reasoning.

Used for the two places where a fast model adds real value to Radar:

1. Concept Normalization - turns a messy idea / GitHub README / PDF text into
   keyword-dense, intent-specific search queries and must-have entities.
2. The relevance gatekeeper - verifies that each Tavily hit genuinely fits the
   user's concept and writes a one-sentence justification.

The client never fabricates facts. Prompts explicitly forbid invented dates,
URLs, rewards, and metrics, and every generated date is treated as a claim that
must have appeared in the supplied result text.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional, Sequence

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_API_URL = "https://api.groq.com/openai/v1/chat/completions"
# Some hosted environments block generic python-http signatures. A normal
# browser-style UA keeps requests on the same path as a regular web client.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def parse_json_content(content: str) -> Optional[Dict[str, Any]]:
    """Parse a model response that may be fenced or surrounded by prose."""

    if not isinstance(content, str) or not content.strip():
        return None
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1] if cleaned.count("```") >= 2 else cleaned[3:]
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


class GroqClient:
    async def generate_json(
        self,
        prompt: str,
        *,
        system: str = "You are a precise structured-data assistant. Return JSON only.",
        max_tokens: int = 1600,
        timeout: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return a parsed JSON object, or ``None`` when Groq is unavailable."""

        key = (settings.GROQ_API_KEY or "").strip()
        if not key or key in {"changeme", "xxx", "placeholder", "your_groq_api_key_here"}:
            return None

        models: Sequence[str] = (
            settings.GROQ_MODEL,
            *tuple(model for model in settings.GROQ_MODEL_FALLBACKS if model != settings.GROQ_MODEL),
        )
        payload_base: Dict[str, Any] = {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "max_completion_tokens": max_tokens,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "User-Agent": _USER_AGENT,
        }

        try:
            async with httpx.AsyncClient(
                timeout=timeout or settings.DOSSIER_V2_SECTION_TIMEOUT_SECONDS
            ) as client:
                for model in models:
                    try:
                        response = await client.post(
                            _API_URL,
                            headers=headers,
                            json={**payload_base, "model": model},
                        )
                        response.raise_for_status()
                        body = response.json()
                        content = body["choices"][0]["message"]["content"]
                        parsed = parse_json_content(content)
                        if parsed is None:
                            logger.warning("Groq returned unparseable JSON from %s", model)
                            return None
                        return parsed
                    except httpx.HTTPStatusError as exc:
                        logger.warning("Groq model %s failed: %s", model, exc.response.status_code)
                        if exc.response.status_code in {401, 403}:
                            return None
                        continue
                    except Exception as exc:  # noqa: BLE001 - provider network boundary
                        logger.warning("Groq model %s failed: %s", model, type(exc).__name__)
                        continue
        except Exception as exc:  # noqa: BLE001 - network boundary
            logger.warning("Groq client unavailable: %s", type(exc).__name__)
        return None

    @property
    def configured(self) -> bool:
        key = (settings.GROQ_API_KEY or "").strip()
        return bool(key) and key not in {
            "changeme",
            "xxx",
            "placeholder",
            "your_groq_api_key_here",
        }


groq_client = GroqClient()
