"""Grounding-provider priority, citation validation, and cache tests."""

import asyncio
import json
import uuid
from datetime import datetime, timezone

import app.services.gemini_client as gemini_module
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.schemas.signals import MarketIntelligenceResponse
from app.services.external_intelligence import ExternalIntelligenceService, external_intelligence
from app.services.gemini_client import gemini_service
from app.services.signal_cache_service import get_or_collect


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeSearchClient:
    def __init__(self, tavily_payload, exa_payload):
        self.payloads = {
            "tavily": FakeResponse(tavily_payload),
            "exa": FakeResponse(exa_payload),
        }
        self.calls = []
        self.exa_kwargs = None

    async def post(self, url, **kwargs):
        provider = "tavily" if "tavily" in url else "exa"
        self.calls.append(provider)
        if provider == "exa":
            self.exa_kwargs = kwargs
        return self.payloads[provider]

    async def aclose(self):
        return None


def test_tavily_is_primary_and_exa_is_only_a_fallback(monkeypatch):
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "tvly-test")
    monkeypatch.setattr(settings, "EXA_API_KEY", "exa-test")

    fake_client = FakeSearchClient(
        {"results": [{"url": "https://example.com/tavily", "title": "Tavily hit", "content": "x"}]},
        {"results": [{"url": "https://example.com/exa", "title": "Exa hit", "text": "y"}]},
    )
    service = ExternalIntelligenceService()
    service._client = fake_client

    results = asyncio.run(service._search_provider("water filter", 3))

    assert [item["url"] for item in results] == ["https://example.com/tavily"]
    assert fake_client.calls == ["tavily"]


def test_exa_is_used_when_tavily_returns_no_results(monkeypatch):
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "tvly-test")
    monkeypatch.setattr(settings, "EXA_API_KEY", "exa-test")

    fake_client = FakeSearchClient(
        {"results": []},
        {"results": [{"url": "https://example.com/exa", "title": "Exa hit", "text": "y"}]},
    )
    service = ExternalIntelligenceService()
    service._client = fake_client

    results = asyncio.run(service._search_provider("water filter", 3))

    assert [item["url"] for item in results] == ["https://example.com/exa"]
    assert fake_client.calls == ["tavily", "exa"]

    payload = fake_client.exa_kwargs["json"]
    assert payload["type"] == "auto"
    assert payload["contents"] == {"highlights": True}
    assert "objective" in payload and payload["objective"].strip()
    assert "category" not in payload
    assert "includeDomains" not in payload


class FakeGeminiClient:
    def __init__(self, *args, **kwargs):
        return None

    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "events": [
                                        {
                                            "title": "Verified Campus Hackathon",
                                            "source_url": "https://events.example.com/real",
                                            "summary": "A real listed event.",
                                            "deadline": "2030-01-01",
                                        },
                                        {
                                            "title": "Fabricated Event",
                                            "source_url": "https://fake.example.com/event",
                                            "summary": "Not in grounding citations.",
                                            "deadline": "2030-01-01",
                                        },
                                        {
                                            "title": "Missing Deadline",
                                            "source_url": "https://events.example.com/real",
                                            "summary": "No explicit deadline.",
                                        },
                                    ]
                                }
                            )
                        }
                    ]
                },
                "groundingMetadata": {
                    "groundingChunks": [
                        {"web": {"uri": "https://events.example.com/real", "title": "Event page"}}
                    ]
                },
            }
        ]
    }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, url, **kwargs):
        return FakeResponse(self.payload)


def test_gemini_events_require_citation_and_explicit_deadline(monkeypatch):
    monkeypatch.setattr(gemini_service, "api_key", "test-key")
    monkeypatch.setattr(gemini_module.httpx, "AsyncClient", FakeGeminiClient)

    events = asyncio.run(
        gemini_service.search_grounded_events("student hackathon 2030", "tech_builder")
    )

    assert len(events) == 1
    assert events[0]["title"] == "Verified Campus Hackathon"
    assert events[0]["canonical_source_url"] == "https://events.example.com/real"
    assert events[0]["decision_metadata"]["is_live"] is True


def test_market_endpoint_serves_second_request_from_cache(monkeypatch):
    calls = {"count": 0}

    async def fake_collect(*, keywords, domain_persona, title=None, max_per_source=3):
        calls["count"] += 1
        return MarketIntelligenceResponse(
            generated_at=datetime.now(timezone.utc),
            domain_persona=domain_persona,
            keywords=list(keywords),
            trend_basis="test snapshot",
            summary="test snapshot",
            signals=[],
            coverage=[],
        )

    monkeypatch.setattr(external_intelligence, "collect_signals", fake_collect)
    keywords = [f"cache-proof-{uuid.uuid4()}"]

    async def scenario():
        async with AsyncSessionLocal() as db:
            first = await get_or_collect(db, keywords, "tech_builder")
            second = await get_or_collect(db, keywords, "tech_builder")
            await db.commit()
            return first, second

    first, second = asyncio.run(scenario())

    assert first.summary == "test snapshot"
    assert second.summary == "test snapshot"
    assert calls["count"] == 1
