"""Model-agnostic LLM client for Dossier v2.

No deterministic template generation exists here. When no provider key is
configured, or every probed model fails, the caller receives an explicit
exception so the API can show a real failure state instead of fabricated text.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
_RETRYABLE_STATUS = {408, 413, 429, 500, 502, 503, 504}
# Groq's on-demand tier allows 8k tokens/minute for this model. Serialising
# those calls and capping requested completion tokens keeps the fallback usable
# during the 18-section parallel synthesis pass.
_GROQ_SEMAPHORE = asyncio.Semaphore(1)
_GROQ_MAX_COMPLETION_TOKENS = 3072
# A dossier makes many model calls in a few minutes. Once a provider returns
# 429/503/413, retrying that model from every section creates a retry storm and
# blows the four-minute budget. Cool it down for the rest of the burst instead.
_MODEL_COOLDOWN = time.monotonic  # injectable in tests
_cooldown_until: Dict[str, float] = {}
_model_cursor: Dict[str, int] = {}
_COOLDOWN_SECONDS = 15.0
_QUOTA_COOLDOWN_SECONDS = 45.0
# Free-tier keys reject a burst of parallel calls even when each individual
# model is healthy. Serialise and pace requests instead of retrying 429s.
_MODEL_LOCKS: Dict[str, asyncio.Lock] = {}
_last_request_at: Dict[str, float] = {}
_MODEL_MIN_INTERVAL = 5.0  # 12 requests/minute per live-tested Gemini model
_GROQ_MIN_INTERVAL = 12.0  # 8k TPM on the on-demand tier


async def _pace(model: str, provider: str) -> None:
    """Keep each model below the free-tier request ceiling."""
    lock = _MODEL_LOCKS.setdefault(model, asyncio.Lock())
    interval = _GROQ_MIN_INTERVAL if provider == "groq" else _MODEL_MIN_INTERVAL
    async with lock:
        wait = interval - (_MODEL_COOLDOWN() - _last_request_at.get(model, 0.0))
        if wait > 0:
            await asyncio.sleep(wait)
        _last_request_at[model] = _MODEL_COOLDOWN()


class LLMNotConfigured(RuntimeError):
    """Raised when no usable API key is present."""


class LLMCallError(RuntimeError):
    """Raised when every configured model in the fallback chain failed."""


def _normalize_usage(raw: Dict[str, Any]) -> Dict[str, int]:
    """Map Gemini/Groq usage fields onto stable snake_case keys."""
    mapping = {
        "prompt_token_count": ("prompt_token_count", "promptTokenCount", "prompt_tokens"),
        "output_token_count": ("output_token_count", "candidatesTokenCount", "completion_tokens"),
        "total_token_count": ("total_token_count", "totalTokenCount", "total_tokens"),
        "thoughts_token_count": ("thoughts_token_count", "thoughtsTokenCount"),
    }
    normalized: Dict[str, int] = {}
    for target, sources in mapping.items():
        for key in sources:
            if raw.get(key) is not None:
                try:
                    normalized[target] = int(raw[key])
                except (TypeError, ValueError):
                    continue
                break
    return normalized


@dataclass
class LLMResult:
    text: str
    parsed: Optional[Any]
    model: str
    latency_ms: int
    usage: Dict[str, int] = field(default_factory=dict)
    cost_usd: float = 0.0
    attempts: int = 1

    @property
    def prompt_tokens(self) -> int:
        return int(self.usage.get("prompt_token_count") or 0)

    @property
    def output_tokens(self) -> int:
        explicit = int(self.usage.get("output_token_count") or 0)
        if explicit:
            return explicit
        total = int(self.usage.get("total_token_count") or 0)
        return max(0, total - self.prompt_tokens)


Hook = Callable[..., Awaitable[None] | None]


def parse_json_text(text: Optional[str]) -> Optional[Any]:
    """Parse strict or fenced JSON without silently accepting prose."""
    if not text:
        return None
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        for opener, closer in (("{", "}"), ("[", "]")):
            start, end = raw.find(opener), raw.rfind(closer)
            if start != -1 and end > start:
                try:
                    return json.loads(raw[start : end + 1])
                except json.JSONDecodeError:
                    continue
    return None


class DossierLLM:
    """Thin REST client with model fallback, token accounting and no fallbacks."""

    def __init__(
        self,
        client: Optional[httpx.AsyncClient] = None,
        on_call: Optional[Hook] = None,
        on_error: Optional[Hook] = None,
    ) -> None:
        self._client = client or httpx.AsyncClient(timeout=120.0, follow_redirects=True)
        self._owns_client = client is None
        self.on_call = on_call
        self.on_error = on_error

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def configured() -> bool:
        return bool(settings.llm_configured)

    @staticmethod
    def _cooling_down(model: str) -> bool:
        return _MODEL_COOLDOWN() < _cooldown_until.get(model, 0.0)

    @staticmethod
    def _cool_down(model: str, status_code: int = 0) -> None:
        seconds = _QUOTA_COOLDOWN_SECONDS if status_code == 429 else _COOLDOWN_SECONDS
        _cooldown_until[model] = _MODEL_COOLDOWN() + seconds
        logger.info("Cooling down %s for %ss after HTTP %s", model, seconds, status_code)

    def _chain(self, role: str) -> List[str]:
        # Only live-probed models. A 429/503 during a real run put the old
        # 3.1-flash-lite and 3-flash-preview ids into a retry storm that ate the
        # four-minute budget without producing a single section.
        configured = (
            settings.DOSSIER_V2_CRITIC_MODEL_CHAIN
            if role == "critic"
            else settings.DOSSIER_V2_MODEL_CHAIN
        )
        seen: set[str] = set()
        models = [m.strip() for m in configured if m and not (m.strip() in seen or seen.add(m.strip()))]
        # A live-probed Groq model is the second provider. Prefixing the id lets
        # one audit trail record both providers with real token usage.
        if settings.groq_configured:
            models.append(f"groq:{settings.DOSSIER_V2_GROQ_MODEL}")
        available = [m for m in models if not self._cooling_down(m)]
        usable = available or models
        # Rotate the first choice so two healthy models share the load instead
        # of hammering one into a 429 while the other sits idle.
        offset = _model_cursor.get(role, 0) % len(usable)
        _model_cursor[role] = _model_cursor.get(role, 0) + 1
        return usable[offset:] + usable[:offset]

    @staticmethod
    def _cost(usage: Dict[str, int], provider: str = "gemini") -> float:
        prompt = int(usage.get("prompt_token_count") or 0)
        output = int(usage.get("output_token_count") or 0)
        if not output:
            total = int(usage.get("total_token_count") or 0)
            output = max(0, total - prompt)
        input_price = (
            settings.DOSSIER_V2_GROQ_PRICE_PER_M_INPUT_USD
            if provider == "groq"
            else settings.DOSSIER_V2_PRICE_PER_M_INPUT_USD
        )
        output_price = (
            settings.DOSSIER_V2_GROQ_PRICE_PER_M_OUTPUT_USD
            if provider == "groq"
            else settings.DOSSIER_V2_PRICE_PER_M_OUTPUT_USD
        )
        return round(
            (prompt / 1_000_000) * input_price
            + (output / 1_000_000) * output_price,
            6,
        )

    async def generate_json(
        self,
        instruction: str,
        prompt: str,
        *,
        role: str = "synthesis",
        max_output_tokens: int = 8192,
        temperature: float = 0.0,
        timeout_seconds: float = 30.0,
    ) -> LLMResult:
        """Return parsed JSON, retrying transient provider-wide 503 bursts."""
        last_error: Optional[LLMCallError] = None
        # Short waves fail fast and retry. Synthesis of a three-section batch
        # needs longer than planning or judging, but still stays under a minute.
        request_timeout = 30.0 if role == "synthesis" else 15.0
        wave_timeout = 40.0 if role == "synthesis" else 22.0
        for wave in range(3):
            try:
                return await asyncio.wait_for(
                    self._generate_json_once(
                        instruction, prompt, role=role, max_output_tokens=max_output_tokens,
                        temperature=temperature, timeout_seconds=min(timeout_seconds, request_timeout),
                    ),
                    timeout=wave_timeout,
                )
            except (LLMCallError, asyncio.TimeoutError) as exc:
                last_error = exc if isinstance(exc, LLMCallError) else LLMCallError("wave timed out")
                transient = "503" in str(exc) or "network error" in str(exc) or isinstance(exc, asyncio.TimeoutError)
                if wave == 2 or not transient:
                    break
                await asyncio.sleep(2.0)
                _cooldown_until.clear()
        assert last_error is not None
        if self.on_error:
            try:
                result = self.on_error(role, self._chain(role), 1, str(last_error)[:2000])
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass
        raise last_error

    async def _generate_json_once(
        self,
        instruction: str,
        prompt: str,
        *,
        role: str = "synthesis",
        max_output_tokens: int = 8192,
        temperature: float = 0.0,
        timeout_seconds: float = 30.0,
    ) -> LLMResult:
        """Return parsed JSON from the first usable model in the chain."""
        if not self.configured():
            raise LLMNotConfigured(
                "AI provider not configured: set GEMINI_API_KEY or GROQ_API_KEY to generate a Dossier v2. "
                "Template output is deliberately disabled."
            )

        errors: List[str] = []
        attempts = 0
        chain = self._chain(role)
        if all(self._cooling_down(model) for model in chain):
            wait = min(_cooldown_until.get(model, 0.0) for model in chain) - _MODEL_COOLDOWN()
            if wait > 0:
                await asyncio.sleep(min(wait, 20.0))
            chain = self._chain(role)
        for model in chain:
            if self._cooling_down(model) and len(chain) > 1:
                errors.append(f"{model}: cooling down")
                continue
            attempts += 1
            started = time.perf_counter()
            provider = "groq" if model.startswith("groq:") else "gemini"
            actual_model = model.split(":", 1)[1] if provider == "groq" else model
            if provider == "gemini":
                url = f"{BASE_URL}/{actual_model}:generateContent"
                headers = {
                    "x-goog-api-key": settings.GEMINI_API_KEY or "",
                    "Content-Type": "application/json",
                }
                payload: Dict[str, Any] = {
                    "contents": [{"parts": [{"text": f"{instruction}\n\n{prompt}"}]}],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "maxOutputTokens": max_output_tokens,
                        "temperature": temperature,
                    },
                }
            else:
                url = GROQ_BASE_URL
                headers = {
                    "Authorization": f"Bearer {(settings.GROQ_API_KEY or '').strip()}",
                    "Content-Type": "application/json",
                    "User-Agent": "LaunchPad-Dossier-v2/1.0",
                }
                payload = {
                    "model": actual_model,
                    "messages": [
                        {"role": "system", "content": instruction},
                        {"role": "user", "content": prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "max_completion_tokens": min(max_output_tokens, _GROQ_MAX_COMPLETION_TOKENS),
                    "temperature": temperature,
                }
            network_failed = False
            for transient in range(3):
                try:
                    await _pace(model, provider)
                    if provider == "groq":
                        async with _GROQ_SEMAPHORE:
                            response = await self._client.post(
                                url, headers=headers, json=payload, timeout=timeout_seconds
                            )
                    else:
                        response = await self._client.post(
                            url, headers=headers, json=payload, timeout=timeout_seconds
                        )
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    errors.append(f"{model}: network error {type(exc).__name__}")
                    self._cool_down(model, 429 if isinstance(exc, httpx.TimeoutException) else 0)
                    logger.warning("Dossier LLM %s network failure %s: %s", model, type(exc).__name__, repr(exc))
                    # A pooled connection can go stale between the probe and
                    # the run. Rebuild it so the next retry starts clean.
                    if self._owns_client and self._client is not None:
                        try:
                            await self._client.aclose()
                        except Exception:
                            pass
                        self._client = httpx.AsyncClient(timeout=120.0, follow_redirects=True)
                    network_failed = True
                    break
                # 503 "high demand" is often transient on Gemini's free tier.
                # A short bounded retry is cheaper than failing the section.
                if response.status_code == 503 and transient < 2:
                    await asyncio.sleep(1.5 * (transient + 1))
                    continue
                break
            if network_failed:
                continue

            if response.status_code != 200:
                try:
                    error_body = response.json()
                except Exception:
                    error_body = {}
                message = str((error_body.get("error") or {}).get("message", ""))[:180] if isinstance(error_body, dict) else ""
                errors.append(f"{model}: HTTP {response.status_code} {message}")
                if response.status_code in _RETRYABLE_STATUS:
                    retry_after = 0
                    if isinstance(error_body, dict):
                        try:
                            retry_after = int(float((error_body.get("error") or {}).get("retry_after_seconds") or 0))
                        except (TypeError, ValueError):
                            retry_after = 0
                    if retry_after:
                        _cooldown_until[model] = _MODEL_COOLDOWN() + min(retry_after + 2, 300)
                    else:
                        self._cool_down(model, response.status_code)
                else:
                    logger.warning("Dossier LLM %s rejected request: %s", model, message)
                continue

            body = response.json()
            if provider == "gemini":
                text = "".join(
                    part.get("text", "")
                    for candidate in body.get("candidates") or []
                    for part in ((candidate.get("content") or {}).get("parts") or [])
                    if isinstance(part, dict)
                )
                usage = _normalize_usage(dict(body.get("usageMetadata") or {}))
            else:
                choices = body.get("choices") or []
                text = str(
                    ((choices[0].get("message") or {}).get("content") or "")
                    if choices and isinstance(choices[0], dict) else ""
                )
                usage = _normalize_usage(dict(body.get("usage") or {}))
            parsed = parse_json_text(text)
            if parsed is None:
                errors.append(f"{model}: response was not valid JSON")
                continue

            result = LLMResult(
                text=text,
                parsed=parsed,
                model=actual_model,
                latency_ms=round((time.perf_counter() - started) * 1000),
                usage=usage,
                cost_usd=self._cost(usage, provider),
                attempts=attempts,
            )
            if self.on_call:
                outcome = self.on_call(result, role)
                if asyncio.iscoroutine(outcome):
                    await outcome
            return result

        error = LLMCallError("All models failed: " + " | ".join(errors[-5:]))
        if self.on_error:
            outcome = self.on_error(role, chain, attempts, str(error))
            if asyncio.iscoroutine(outcome):
                await outcome
        raise error

    async def embed(self, text: str, dimensions: int = 768) -> Optional[List[float]]:
        """Real embeddings only; returns None when unavailable."""
        if not self.configured():
            return None
        try:
            response = await self._client.post(
                f"{BASE_URL}/{settings.GEMINI_EMBEDDING_MODEL}:embedContent",
                headers={"x-goog-api-key": settings.GEMINI_API_KEY or ""},
                json={
                    "model": f"models/{settings.GEMINI_EMBEDDING_MODEL}",
                    "content": {"parts": [{"text": text[:2000]}]},
                    "outputDimensionality": dimensions,
                },
            )
            if response.status_code != 200:
                return None
            values = (response.json().get("embedding") or {}).get("values") or []
            return [float(v) for v in values] or None
        except Exception:
            return None


llm_client = DossierLLM()
