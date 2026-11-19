"""Intent-specific Radar query planning, gatekeeping, reranking, and live scan."""

import asyncio
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import app.services.gemini_client as gemini_module
import app.services.radar_live_service as live_module
from app.api.v1.radar import router as radar_router
from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.schemas.radar import RadarBriefingResponse
from app.services.external_intelligence import ExternalIntelligenceService
from app.services.gemini_client import gemini_service
from app.services.opportunity_discovery import DiscoveryResult, SourceResult
from app.services.radar_engine import build_briefing


def test_query_generation_keeps_required_intent_templates(monkeypatch):
    async def fake_json(prompt):
        return {
            "domain": "rural water",
            "core_problem_or_tech": "low-cost water filtration",
            "problem_statement": "rural households lack safe water",
            "solution_type": "maintenance-free filter",
        }

    monkeypatch.setattr(gemini_service, "_generate_json_prompt", fake_json)

    queries = asyncio.run(
        gemini_service.generate_radar_queries(
            {
                "persona": "tech_builder",
                "problem_statement": "rural households lack safe water",
                "tech_stack": ["Python"],
            },
            "en",
        )
    )

    assert queries["hackathons"] == "rural water hackathon OR buildathon registration open 2026"
    assert queries["news"] == "low-cost water filtration launch OR release OR funding"
    assert queries["builders"] == (
        "building rural households lack safe water OR looking for maintenance-free filter"
    )


def test_gatekeeper_rejects_root_profiles_and_search_pages():
    assert live_module.is_actionable_url("https://x.com/someone") is False
    assert live_module.is_actionable_url("https://x.com/someone/status/12345") is True
    assert live_module.is_actionable_url("https://www.reddit.com/r/python/") is False
    assert live_module.is_actionable_url("https://www.reddit.com/r/python/comments/abc/title/") is True
    assert live_module.is_actionable_url("https://www.google.com/search?q=hackathon") is False
    assert live_module.is_actionable_url("https://devpost.com/hackathons") is False
    assert live_module.is_actionable_url("https://devpost.com/hackathons/ai-sprint-2026") is True


def test_rerank_drops_low_score_and_wrong_language(monkeypatch):
    async def fake_json(prompt):
        return {
            "results": [
                {"id": "a", "score": 92, "language": "en", "reason": "direct fit"},
                {"id": "b", "score": 40, "language": "en", "reason": "generic"},
                {"id": "c", "score": 88, "language": "hi", "reason": "wrong language"},
            ]
        }

    monkeypatch.setattr(gemini_service, "_generate_json_prompt", fake_json)

    items = [
        {"id": "a", "title": "Water filter pilot", "summary": "Rural water filtration", "url": "https://example.com/a"},
        {"id": "b", "title": "FastAPI frameworks", "summary": "Old Reddit thread", "url": "https://example.com/b"},
        {"id": "c", "title": "Another result", "summary": "Hindi discussion", "url": "https://example.com/c"},
    ]

    accepted = asyncio.run(
        gemini_service.rerank_radar_results(
            items,
            "A low-cost water filter for rural households",
            "builders",
            language="en",
        )
    )

    assert [item["id"] for item in accepted] == ["a"]
    assert accepted[0]["relevance_score_100"] == 92


def test_tavily_intent_search_sends_advanced_recency_params(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"results": [{"url": "https://devpost.com/hackathons/x", "title": "Hack"}]}

    class FakeClient:
        async def post(self, url, **kwargs):
            captured.update(kwargs.get("json") or {})
            return FakeResponse()

        async def aclose(self):
            return None

    monkeypatch.setattr(settings, "TAVILY_API_KEY", "tvly-test")
    monkeypatch.setattr(settings, "EXA_API_KEY", None)
    service = ExternalIntelligenceService(client=FakeClient())

    results = asyncio.run(service.search_for_intent("rural water hackathon", intent="hackathons"))

    assert len(results) == 1
    assert captured["search_depth"] == "advanced"
    assert captured["time_range"] == "month"
    assert captured["filter_by_published_date"] is True
    assert captured["include_published_date"] is True
    assert captured["include_domains"] == list(settings.RADAR_HACKATHON_DOMAINS)
    assert captured["max_results"] == settings.RADAR_TAVILY_MAX_RESULTS
    assert "topic" not in captured

    asyncio.run(service.search_for_intent("water launch", intent="news"))
    assert captured["topic"] == "news"
    assert captured["time_range"] == settings.RADAR_TAVILY_NEWS_TIME_RANGE


class FakeResult:
    def scalars(self):
        return self

    def all(self):
        return []


class FakeDB:
    async def execute(self, statement):
        return FakeResult()


def test_scan_live_endpoint_returns_fresh_briefing_without_fallback_cards(monkeypatch):
    async def fake_db():
        yield FakeDB()

    sentinel = {
        "status": "ok",
        "persona": "tech_builder",
        "language": "en",
        "max_age_hours": 0,
        "queries": [],
        "stats": {
            "raw_results": 12,
            "actionable_after_gatekeeper": 7,
            "accepted": 3,
            "rejected": 9,
            "opportunities_inserted": 1,
            "opportunities_merged": 0,
            "duration_ms": 42,
        },
        "briefing": build_briefing([], "tech_builder"),
        "signals": [],
    }

    async def fake_scan_live(**kwargs):
        return sentinel

    monkeypatch.setattr("app.api.v1.radar.run_live_scan", fake_scan_live)
    app.dependency_overrides[get_db] = fake_db
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/radar/scan-live",
            json={"raw_idea": "A low-cost water filter for rural households", "persona": "tech_builder"},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    body = response.json()
    assert body["stats"]["accepted"] == 3
    assert body["briefing"]["all_opportunities"] == []
    assert all(signal.get("is_live") is not False for signal in body["signals"])


def test_verification_placeholders_are_rejected_before_rerank():
    item = live_module._normalise_raw_item(
        {
            "url": "https://www.google.com/search?q=hackathon",
            "title": "Verification link — not a scraped post",
            "content": "Open the search results to confirm.",
        },
        intent="hackathons",
        query="test",
    )
    assert item is None


def test_scan_live_uses_direct_source_candidates(monkeypatch):
    candidate = {
        "title": "AI Water Hack",
        "category": "hackathon",
        "canonical_source_url": "https://ai-water.devpost.com/",
        "host_organization": "Open Water Labs",
        "deadline": datetime.now(timezone.utc) + timedelta(days=5),
        "description": "A real Devpost listing.",
        "tags": ["AI", "Water"],
        "domain_personas": ["tech_builder"],
        "location_type": "virtual",
        "reward_pool": "$10,000",
        "decision_metadata": {"source": "devpost", "is_live": True, "match_score": 0.8},
    }
    captured = {}

    async def fake_discovery(**kwargs):
        captured["idea"] = kwargs.get("raw_idea")
        return DiscoveryResult(
            query="ai water",
            candidates=[candidate],
            sources=[
                SourceResult(
                    source="devpost",
                    label="Devpost",
                    status="ok",
                    raw_count=12,
                    is_official=True,
                )
            ],
        )

    async def fake_upsert(db, candidates):
        captured["candidates"] = candidates
        return {"inserted": 1, "merged": 0, "skipped": 0}

    monkeypatch.setattr(live_module, "discover_opportunities", fake_discovery)
    monkeypatch.setattr("app.services.opportunity_scout.upsert_candidates", fake_upsert)

    result = asyncio.run(
        live_module.scan_live(
            db=FakeDB(),
            dossier=None,
            raw_idea="AI water filter",
            persona="tech_builder",
            intents=["hackathons"],
            language="en",
            max_age_hours=0,
        )
    )

    assert captured["idea"] == "AI water filter"
    assert captured["candidates"][0]["canonical_source_url"] == candidate["canonical_source_url"]
    assert result["sources"][0]["label"] == "Devpost"
    assert result["stats"]["raw_results"] >= 12
    assert result["stats"]["opportunities_inserted"] == 1
    assert result["queries"][0]["intent"] == "opportunities"
