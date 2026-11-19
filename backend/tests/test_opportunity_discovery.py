"""Direct-source opportunity discovery: normalisation, provenance, dedupe."""

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone

from app.models.opportunity import Opportunity
from app.services.opportunity_discovery import (
    DiscoveryResult,
    SourceResult,
    deduplicate_candidates,
    discover_opportunities,
)
from app.services.radar_engine import build_briefing

NOW = datetime.now(timezone.utc)
FUTURE = NOW + timedelta(days=30)
FUTURE_ISO = FUTURE.isoformat()
FUTURE_US = FUTURE.strftime("%m/%d/%Y")
FUTURE_LONG = FUTURE.strftime("%b %d, %Y")


class FakeResponse:
    def __init__(self, payload=None, text=""):
        self._payload = payload
        self.text = text

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    async def get(self, url, params=None, **kwargs):
        self.calls.append(("GET", url, params))
        return self.routes[url]

    async def post(self, url, json=None, **kwargs):
        self.calls.append(("POST", url, json))
        return self.routes[url]

    async def aclose(self):
        return None


def _mlh_html():
    payload = {
        "component": "SeasonEvents/Index",
        "props": {
            "upcomingEvents": [
                {
                    "name": "MLH AI Build Sprint",
                    "startsAt": FUTURE_ISO,
                    "endsAt": FUTURE_ISO,
                    "url": "/events/ai-build-sprint/prizes",
                    "location": "Online",
                    "formatType": "virtual",
                    "formatLabel": "Virtual",
                    "customFields": {"hackathon_focus": ["Software", "AI"]},
                }
            ]
        },
    }
    return f'<html><script data-page="app" type="application/json">{json.dumps(payload)}</script></html>'


def _commudle_rss():
    return f"""<?xml version="1.0"?>
    <rss version="2.0"><channel>
      <item>
        <title>Commudle AI Build Night {FUTURE_LONG}</title>
        <link>https://www.commudle.com/communities/ai-club/events/build-night</link>
        <description>Registrations close {FUTURE_LONG}.</description>
        <pubDate>{NOW.strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
      </item>
    </channel></rss>"""


def _routes():
    year = NOW.year
    return {
        "https://devpost.com/api/hackathons": FakeResponse(
            {
                "hackathons": [
                    {
                        "title": "AI Water Hack",
                        "url": "https://ai-water.devpost.com/",
                        "organization_name": "Open Water Labs",
                        "submission_period_dates": FUTURE_LONG,
                        "themes": [{"name": "Machine Learning/AI"}],
                        "prize_amount": "$<span data-currency-value>100,000</span>",
                        "displayed_location": {"location": "Online"},
                    }
                ]
            }
        ),
        "https://unstop.com/api/public/opportunity/search-result": FakeResponse(
            {
                "data": {
                    "data": [
                        {
                            "title": "Water Filter Innovation Challenge",
                            "seo_url": "https://unstop.com/hackathons/water-filter-innovation-1",
                            "end_date": FUTURE_ISO,
                            "details": "<p>Build a low-cost water filter.</p>",
                            "region": "hybrid",
                            "organisation": {"name": "IIT Bombay"},
                            "address_with_country_logo": {"city": "Mumbai"},
                            "required_skills": [{"skill_name": "Artificial Intelligence (AI)"}],
                            "prizes": [{"cash": 100000, "currencyCode": "INR"}],
                        }
                    ]
                }
            }
        ),
        "https://api.lu.ma/discover/get-paginated-events": FakeResponse(
            {
                "entries": [
                    {
                        "event": {
                            "name": "AI for Public Health Meetup",
                            "url": "ai-public-health",
                            "start_at": FUTURE_ISO,
                            "end_at": FUTURE_ISO,
                            "location_type": "offline",
                            "geo_address_info": {"city": "Pune"},
                            "description": "A community meetup on applied AI for public health.",
                        }
                    }
                ]
            }
        ),
        f"https://www.mlh.com/seasons/{year}/events": FakeResponse(text=_mlh_html()),
        f"https://www.mlh.com/seasons/{year + 1}/events": FakeResponse(text=_mlh_html()),
        "https://api.grants.gov/v1/api/search2": FakeResponse(
            {
                "data": {
                    "oppHits": [
                        {
                            "id": "12345",
                            "number": " NSF-26-001",
                            "title": "Water Infrastructure Research Grant",
                            "agencyName": "National Science Foundation",
                            "openDate": NOW.strftime("%m/%d/%Y"),
                            "closeDate": FUTURE_US,
                            "oppStatus": "posted",
                            "fundingCategories": "Engineering",
                        }
                    ]
                }
            }
        ),
        "https://news.google.com/rss/search": FakeResponse(text=_commudle_rss()),
        "https://hackalendar.com/api/events": FakeResponse(
            {
                "data": [
                    {
                        "name": "Civic AI Hackathon",
                        "url": "https://hackalendar.com/e/civic-ai-hackathon",
                        "description": "Build civic tools with AI.",
                        "registrationDeadline": FUTURE_ISO,
                        "startAt": FUTURE_ISO,
                        "endAt": FUTURE_ISO,
                        "organizer": "Civic Tech Community",
                        "cityLabel": "Bengaluru",
                        "themes": ["AI", "Civic Tech"],
                        "mode": "hybrid",
                        "prizePool": "$5,000",
                    }
                ]
            }
        ),
    }


def test_discover_opportunities_normalizes_real_sources_with_provenance():
    result = asyncio.run(
        discover_opportunities(
            raw_idea="low-cost water filter and AI public health tool",
            persona="tech_builder",
            client=FakeClient(_routes()),
        )
    )

    sources = {item.source for item in result.sources}
    assert {"devpost", "mlh", "unstop", "luma", "grants_gov", "commudle", "hackalendar"}.issubset(sources)
    assert result.candidates
    assert all(item["deadline"] > NOW for item in result.candidates)
    assert all(item["canonical_source_url"].startswith("https://") for item in result.candidates)

    by_source = {item["decision_metadata"]["source"]: item for item in result.candidates}
    assert by_source["devpost"]["host_organization"] == "Open Water Labs"
    assert by_source["devpost"]["reward_pool"] == "$100,000"
    assert by_source["devpost"]["decision_metadata"]["source_kind"] == "public_api"
    assert by_source["devpost"]["decision_metadata"]["deadline_basis"] == "submission_period"
    assert by_source["unstop"]["city"] == "Mumbai"
    assert by_source["unstop"]["decision_metadata"]["deadline_basis"] == "registration_deadline"
    assert "mlh" not in by_source
    assert "luma" not in by_source
    assert by_source["grants_gov"]["category"] == "grant"
    assert by_source["grants_gov"]["decision_metadata"]["deadline_basis"] == "application_close_date"
    assert by_source["commudle"]["decision_metadata"]["verification"] == "verify_on_official_page"
    assert (
        by_source["commudle"]["decision_metadata"]["deadline_basis"]
        == "registration_deadline_in_search_snippet"
    )
    assert by_source["hackalendar"]["reward_pool"] == "$5,000"
    assert by_source["hackalendar"]["decision_metadata"]["deadline_basis"] == "registration_deadline"

    source_health = {item.source: item for item in result.sources}
    assert source_health["mlh"].status == "empty"
    assert "registration deadline" in (source_health["mlh"].note or "")
    assert source_health["luma"].status == "empty"
    assert "registration deadline" in (source_health["luma"].note or "")

    assert all(item["decision_metadata"]["is_live"] is True for item in result.candidates)
    assert all(item["domain_personas"] == ["tech_builder"] for item in result.candidates)


def test_deduplicate_candidates_merges_tags_and_keeps_strongest_match():
    base = {
        "title": "Shared Hackathon",
        "category": "hackathon",
        "canonical_source_url": "https://devpost.com/hackathons/shared/",
        "deadline": FUTURE,
        "description": "A real listing",
        "tags": ["AI"],
        "domain_personas": ["tech_builder"],
        "location_type": "virtual",
    }
    weak = {
        **base,
        "decision_metadata": {"source": "search_result", "match_score": 0.2},
    }
    strong = {
        **base,
        "canonical_source_url": "https://devpost.com/hackathons/shared",
        "tags": ["Water"],
        "domain_personas": ["design_biotech"],
        "decision_metadata": {"source": "devpost", "match_score": 0.8},
    }

    merged = deduplicate_candidates([weak, strong])
    assert len(merged) == 1
    assert merged[0]["decision_metadata"]["source"] == "devpost"
    assert set(merged[0]["tags"]) == {"AI", "Water"}
    assert set(merged[0]["domain_personas"]) == {"tech_builder", "design_biotech"}


def test_empty_sources_do_not_produce_cards():
    routes = _routes()
    for key, response in routes.items():
        routes[key] = FakeResponse({}, "")
    result = asyncio.run(
        discover_opportunities(
            raw_idea="quantum bread knife",
            persona="tech_builder",
            client=FakeClient(routes),
        )
    )
    assert result.candidates == []
    assert all(item.status in {"empty", "error"} for item in result.sources)


def test_seed_rows_are_hidden_from_live_briefing():
    seed = Opportunity(
        id=uuid.uuid4(),
        title="Seed Demo Hackathon",
        category="hackathon",
        canonical_source_url=f"https://example.com/{uuid.uuid4().hex}",
        host_organization="Seed Lab",
        deadline=FUTURE,
        description="A seeded demo record.",
        tags=["AI"],
        domain_personas=["tech_builder"],
        location_type="virtual",
        decision_metadata={"source": "seed", "is_live": True},
        sha256_hash=uuid.uuid4().hex + uuid.uuid4().hex,
    )
    briefing = build_briefing([seed], "tech_builder", now=NOW)
    assert briefing.all_opportunities == []
    assert briefing.strongest_pick is None


def test_discovery_result_payload_exposes_source_health():
    result = DiscoveryResult(
        query="ai water",
        candidates=[],
        sources=[SourceResult("devpost", "Devpost", status="ok", raw_count=5, is_official=True)],
    )
    payload = result.source_payload()
    assert payload[0]["label"] == "Devpost"
    assert payload[0]["raw_count"] == 5
    assert payload[0]["accepted_count"] == 0
    assert payload[0]["is_official"] is True


def _live_opportunity(*, deadline: datetime, source: str, basis: str) -> Opportunity:
    return Opportunity(
        id=uuid.uuid4(),
        title=f"{source} opportunity",
        category="hackathon",
        canonical_source_url=f"https://example.com/{uuid.uuid4().hex}",
        host_organization="Example Host",
        deadline=deadline,
        description="A live source-backed opportunity.",
        tags=["AI"],
        domain_personas=["tech_builder"],
        location_type="virtual",
        decision_metadata={
            "source": source,
            "is_live": True,
            "deadline_basis": basis,
        },
        sha256_hash=uuid.uuid4().hex + uuid.uuid4().hex,
    )


def test_event_end_only_rows_are_hidden_from_live_briefing():
    event_end_only = _live_opportunity(
        deadline=FUTURE,
        source="mlh",
        basis="event_end",
    )
    briefing = build_briefing([event_end_only], "tech_builder", now=NOW)
    assert briefing.all_opportunities == []
    assert briefing.strongest_pick is None


def test_expired_registration_rows_are_hidden_from_live_briefing():
    expired = _live_opportunity(
        deadline=NOW - timedelta(days=1),
        source="devpost",
        basis="submission_period",
    )
    briefing = build_briefing([expired], "tech_builder", now=NOW)
    assert briefing.all_opportunities == []
    assert briefing.strongest_pick is None


def test_commudle_snippet_without_registration_language_is_not_promoted():
    routes = _routes()
    routes["https://news.google.com/rss/search"] = FakeResponse(
        text=f"""<?xml version="1.0"?>
        <rss version="2.0"><channel>
          <item>
            <title>Commudle AI Build Night {FUTURE_LONG}</title>
            <link>https://www.commudle.com/communities/ai-club/events/build-night</link>
            <description>Event happens {FUTURE_LONG}.</description>
            <pubDate>{NOW.strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
          </item>
        </channel></rss>"""
    )
    result = asyncio.run(
        discover_opportunities(
            raw_idea="low-cost AI water filter",
            persona="tech_builder",
            client=FakeClient(routes),
        )
    )
    assert all(
        item["decision_metadata"]["source"] != "commudle" for item in result.candidates
    )
