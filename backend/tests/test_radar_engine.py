import uuid
from datetime import datetime, timedelta, timezone

from app.models.dossier import ProjectDossier
from app.models.opportunity import Opportunity
from app.services.radar_engine import (
    build_briefing,
    networking_plan,
    opportunity_bucket,
    score_opportunity,
    to_opportunity_base,
)

NOW = datetime.now(timezone.utc)


def make_opportunity(
    *,
    title: str,
    category: str = "hackathon",
    hours_from_now: float = 24,
    location_type: str = "virtual",
    city=None,
    personas=None,
) -> Opportunity:
    return Opportunity(
        id=uuid.uuid4(),
        title=title,
        category=category,
        canonical_source_url=f"https://example.com/{uuid.uuid4().hex}",
        host_organization="Example Foundation",
        deadline=NOW + timedelta(hours=hours_from_now),
        city=city,
        event_date=(NOW + timedelta(hours=hours_from_now)).date(),
        description="A test opportunity description.",
        tags=["AI", "Systems"],
        domain_personas=personas if personas is not None else ["tech_builder"],
        location_type=location_type,
        reward_pool="$10,000",
        decision_metadata={},
        embedding=None,
        sha256_hash=uuid.uuid4().hex + uuid.uuid4().hex,
    )


def make_dossier() -> ProjectDossier:
    return ProjectDossier(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        slug="edge-kernel-abc123",
        title="Edge Kernel",
        tagline="Sub-millisecond local inference",
        domain_persona="tech_builder",
        stage="Prototype",
        problem_statement="Edge devices cannot run large models.",
        solution_breakdown={"architecture": "Ternary SIMD kernel."},
        tech_stack=["Rust", "C++", "NEON"],
        key_metrics=[{"label": "Latency", "value": "12ms"}],
        whitespace_analysis={"market_gap": "No open edge stack.", "top_voices": []},
        missing_roles=[{"role": "Embedded Engineer", "reason": "Tune NEON paths."}],
        external_links={"github": "https://github.com/example/edge"},
        verified_status=False,
        boosted=False,
        embedding=None,
    )


def test_briefing_filters_expired_and_splits_categories():
    opportunities = [
        make_opportunity(title="Expired Hackathon", category="hackathon", hours_from_now=-5),
        make_opportunity(title="Urgent Hackathon", category="hackathon", hours_from_now=24),
        make_opportunity(title="General Fellowship", category="fellowship", hours_from_now=120),
    ]
    briefing = build_briefing(opportunities, "tech_builder", now=NOW)

    titles = [item.title for item in briefing.all_opportunities]
    assert "Expired Hackathon" not in titles
    assert "Urgent Hackathon" in titles
    assert "General Fellowship" in titles
    assert [item.title for item in briefing.hackathons] == ["Urgent Hackathon"]
    assert [item.title for item in briefing.general_events] == ["General Fellowship"]

    assert briefing.strongest_pick is not None
    assert briefing.strongest_pick.match_score > 0
    assert len(briefing.urgent_deadlines) == 1
    assert briefing.urgent_deadlines[0].hours_remaining <= 24


def test_briefing_prefers_city_matches():
    opportunities = [
        make_opportunity(
            title="Delhi Build Sprint",
            category="build_sprint",
            hours_from_now=48,
            location_type="in_person",
            city="Delhi",
        ),
        make_opportunity(
            title="Pune Build Sprint",
            category="build_sprint",
            hours_from_now=48,
            location_type="in_person",
            city="Pune",
        ),
    ]
    briefing = build_briefing(opportunities, "tech_builder", now=NOW, city="Pune")
    assert briefing.all_opportunities[0].title == "Pune Build Sprint"


def test_posted_plan_has_two_starters_and_prelinked_followup():
    opportunity = make_opportunity(title="Global Robotics Hackathon")
    dossier = make_dossier()
    plan = networking_plan(opportunity, "tech_builder", dossier, city="Pune")

    assert len(plan.conversation_starters) == 2
    assert plan.icebreaker_message == plan.conversation_starters[0]
    assert "Edge Kernel" in plan.conversation_starters[0]
    assert "12ms" in plan.conversation_starters[0]
    assert "https://studentradar.dev/p/edge-kernel-abc123" in plan.followup_draft
    assert plan.target_stakeholders


def test_global_opportunities_match_every_persona():
    opportunity = make_opportunity(title="Open Global Grant", personas=[])
    briefing = build_briefing([opportunity], "design_biotech", now=NOW)
    assert len(briefing.all_opportunities) == 1


def test_other_personas_events_do_not_leak_into_fallback():
    opportunity = make_opportunity(
        title="Policy-only Fellowship",
        category="fellowship",
        personas=["policy_law"],
    )
    briefing = build_briefing([opportunity], "tech_builder", now=NOW)
    assert briefing.all_opportunities == []
    assert briefing.strongest_pick is None


def test_unknown_category_falls_back_to_general_event():
    assert opportunity_bucket(make_opportunity(title="X", category="conference")) == "general_event"
    assert opportunity_bucket(make_opportunity(title="Y", category="hackathon")) == "hackathon"
    assert opportunity_bucket(make_opportunity(title="Z", category="build_sprint")) == "hackathon"


def test_score_is_bounded_and_reward_adds_signal():
    opportunity = make_opportunity(title="Reward Event")
    score = score_opportunity(opportunity, "tech_builder", now=NOW)
    assert 0.0 <= score <= 1.0


def test_briefing_hides_legacy_verification_links():
    opportunity = make_opportunity(title="Verify opportunities", hours_from_now=72)
    opportunity.decision_metadata = {"source": "search_link", "is_live": False}
    briefing = build_briefing([opportunity], "tech_builder", now=NOW)
    assert briefing.all_opportunities == []
    assert briefing.strongest_pick is None


def test_to_opportunity_base_exposes_spec_aliases():
    opportunity = make_opportunity(title="City Event", city="Pune", location_type="in_person")
    base = to_opportunity_base(opportunity)
    assert base.organizer == "Example Foundation"
    assert base.mode == "in_person"
    assert base.deadline_at == base.deadline
    assert base.persona_tags == ["tech_builder"]
