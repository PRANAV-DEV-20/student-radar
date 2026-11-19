"""Tests for cross-platform signal discovery and fallback safety."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.external_intelligence import (
    SUPPORTED_SOURCES,
    ExternalIntelligenceService,
)

client = TestClient(app)


@pytest.fixture
def no_provider(monkeypatch):
    monkeypatch.setattr(settings, "TAVILY_API_KEY", None)
    monkeypatch.setattr(settings, "EXA_API_KEY", None)
    monkeypatch.setattr(settings, "ENABLE_EXTERNAL_INTELLIGENCE", True)


def test_market_endpoint_covers_sources_without_provider_keys(no_provider):
    response = client.get(
        "/api/v1/signals/market",
        params={"keywords": "water filter,low-cost", "persona": "tech_builder"},
    )
    assert response.status_code == 200

    body = response.json()
    assert {item["source"] for item in body["signals"]} == set(SUPPORTED_SOURCES)
    assert all(item["is_live"] is False for item in body["signals"])
    assert all(item["url"].startswith("https://") for item in body["signals"])
    assert body["keywords"] == ["water filter", "low-cost"]
    assert body["trend_direction"] == "unknown"
    assert "no posts or metrics were invented" in body["summary"]

    reddit = next(item for item in body["signals"] if item["source"] == "reddit")
    trends = next(item for item in body["signals"] if item["source"] == "google_trends")
    assert "reddit.com" in reddit["url"]
    assert "trends.google.com" in trends["url"]
    assert all(not item["live"] for item in body["coverage"])


def test_sources_endpoint_lists_all_platforms(no_provider):
    response = client.get("/api/v1/signals/sources")
    assert response.status_code == 200
    body = response.json()
    assert {item["id"] for item in body["sources"]} == set(SUPPORTED_SOURCES)
    assert body["grounding_providers"] == []


def test_live_results_are_deduped_scored_and_linked_to_builders(monkeypatch):
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "test-key")
    monkeypatch.setattr(settings, "EXA_API_KEY", None)
    monkeypatch.setattr(settings, "ENABLE_EXTERNAL_INTELLIGENCE", True)

    reddit_results = [
        {
            "title": "Low-cost water filter for rural households",
            "url": "https://www.reddit.com/r/engineering/comments/abc123/filter/",
            "content": "We need a low-cost water filter that is easy to maintain.",
            "score": 0.9,
            "published_date": "2026-11-01T10:00:00Z",
        },
        {
            "title": "Duplicate thread",
            "url": "https://reddit.com/r/engineering/comments/abc123/filter",
            "content": "low-cost water filter discussion",
            "score": 0.2,
        },
    ]
    founder_results = [
        {
            "title": "Startup building low-cost water filter",
            "url": "https://www.founderdb.com/company/water-filter/",
            "content": "A startup working on a low-cost water filter.",
            "score": 0.7,
        }
    ]

    async def fake_search(query, max_results):
        if "site:reddit.com" in query:
            return reddit_results
        if "site:founderdb.com" in query:
            return founder_results
        return []

    service = ExternalIntelligenceService()
    monkeypatch.setattr(service, "_search_provider", fake_search)

    result = asyncio.run(
        service.collect_signals(
            keywords=["low-cost water filter"],
            domain_persona="tech_builder",
            title="Water Filter",
            max_per_source=3,
        )
    )

    urls = [signal.url for signal in result.signals]
    assert urls.count("https://www.reddit.com/r/engineering/comments/abc123/filter/") == 1
    assert len(urls) == len(set(urls))

    reddit_signal = next(signal for signal in result.signals if signal.source == "reddit")
    assert reddit_signal.is_live is True
    assert reddit_signal.relevance_score > 0.5
    assert reddit_signal.published_at is not None
    assert "low-cost water filter" in reddit_signal.keywords

    coverage = {item.source: item for item in result.coverage}
    assert coverage["reddit"].live is True
    assert coverage["google_trends"].live is False
    assert result.trend_direction == "emerging"
    assert result.similar_builders
    assert result.similar_builders[0].platform == "reddit"
    assert "reddit.com" in result.similar_builders[0].profile_url


def test_disabled_collection_returns_only_exploration_links(monkeypatch):
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "test-key")
    monkeypatch.setattr(settings, "EXA_API_KEY", None)
    monkeypatch.setattr(settings, "ENABLE_EXTERNAL_INTELLIGENCE", False)

    result = asyncio.run(
        ExternalIntelligenceService().collect_signals(
            keywords=["climate"], domain_persona="design_biotech"
        )
    )
    assert all(not signal.is_live for signal in result.signals)
    assert all(not item.live for item in result.coverage)
    assert "disabled" in result.coverage[0].note
