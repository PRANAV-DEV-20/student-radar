import asyncio
from datetime import datetime, timezone

from app.services.opportunity_scout import (
    _authority,
    _infer_category,
    _parse_deadline,
    collect_candidates,
    upsert_candidates,
)


class FakeResult:
    def scalars(self):
        return self

    def first(self):
        return None

    def scalar_one_or_none(self):
        return None


class FakeSession:
    def __init__(self):
        self.added = []
        self.flushed = 0

    async def execute(self, statement):
        return FakeResult()

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed += 1


def test_parse_deadline_uses_explicit_iso_date():
    deadline, inferred = _parse_deadline("Applications close 2099-01-15 at midnight.")
    assert inferred is False
    assert deadline.year == 2099
    assert deadline.month == 1
    assert deadline.day == 15


def test_parse_deadline_falls_back_and_marks_inferred():
    deadline, inferred = _parse_deadline("No date in this snippet.", fallback_days=14)
    assert inferred is True
    assert (deadline - datetime.now(timezone.utc)).days >= 13


def test_category_inference():
    assert _infer_category("Global AI Hackathon", "") == "hackathon"
    assert _infer_category("Research Grant for Students", "") == "grant"
    assert _infer_category("Policy Fellowship 2026", "") == "fellowship"
    assert _infer_category("Annual Conference", "talks and panels") == "general_event"


def test_domain_authority_ranking():
    assert _authority("https://devpost.com/hackathons/x") == 3
    assert _authority("https://www.devpost.com/hackathons/x") == 3
    assert _authority("https://nsf.gov/funding/x") >= 2
    assert _authority("https://random-blog.example.com/x") == 1


def test_catalog_never_contains_verification_links(monkeypatch):
    import app.services.radar_live_service as live_module

    async def fake_collect(**kwargs):
        return live_module.IntentScanResult(intent="hackathons", query="x")

    monkeypatch.setattr(live_module, "collect_intent_candidates", fake_collect)

    assert collect_candidates() == []


def _candidate() -> dict:
    return {
        "title": "Verified Student Hackathon",
        "category": "hackathon",
        "canonical_source_url": "https://devpost.com/hackathons/verified-student-2030",
        "host_organization": "devpost.com",
        "deadline": datetime(2099, 1, 15, tzinfo=timezone.utc),
        "description": "A real listed build sprint with an explicit deadline.",
        "tags": ["AI"],
        "domain_personas": ["tech_builder"],
        "location_type": "virtual",
        "reward_pool": None,
        "decision_metadata": {"source": "tavily_intent_scan", "is_live": True},
    }


def test_upsert_inserts_candidates_with_spec_fields():
    session = FakeSession()
    candidates = [_candidate()]
    result = asyncio.run(upsert_candidates(session, candidates))

    assert result == {"inserted": len(candidates), "merged": 0, "skipped": 0}
    assert session.flushed == 1
    assert len(session.added) == len(candidates)
    first = session.added[0]
    assert first.sha256_hash
    assert first.embedding
    assert first.event_date is not None
    assert first.decision_metadata
