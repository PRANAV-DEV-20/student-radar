"""Opportunity matching / briefing helpers.

Kept separate from the router so the same logic can be reused by Celery
briefing workers and by tests.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List, Optional, Sequence, Tuple

from app.core.config import settings
from app.models.dossier import ProjectDossier
from app.models.opportunity import Opportunity
from app.schemas.radar import (
    NetworkingPlan,
    OpportunityBase,
    RadarBriefingResponse,
    StrongestPick,
    UrgentDeadline,
)
from app.services.dedup_service import dedup_service

PERSONA_LABELS = {
    "tech_builder": "Engineering & AI Systems",
    "policy_law": "Law, Governance & Policy",
    "business_finance": "Finance, Quant & Venture",
    "design_biotech": "Biotech & Industrial Design",
}

_HACKATHON_CATEGORIES = {
    "hackathon",
    "hackathons",
    "build_sprint",
    "build_sprints",
    "build-sprint",
    "build-sprints",
}


def as_utc(value: datetime) -> datetime:
    """Normalize DB datetimes to timezone-aware UTC values."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def is_expired(opportunity: Opportunity, now: Optional[datetime] = None) -> bool:
    now = now or datetime.now(timezone.utc)
    return as_utc(opportunity.deadline) <= now


_REGISTRATION_DEADLINE_BASES = {
    "submission_period",
    "registration_deadline",
    "application_close_date",
    "explicit_deadline",
    "registration_deadline_in_search_snippet",
    # A future, explicitly stated event date is actionable even when a
    # registration deadline is not published in the search snippet.
    "event_date",
}


def is_radar_ready(opportunity: Opportunity) -> bool:
    """Hide legacy links, client demos, and seed rows from the live radar feed."""

    metadata = opportunity.decision_metadata or {}
    if metadata.get("is_live") is False:
        return False
    source = str(metadata.get("source") or "").strip().lower()
    return source not in {"search_link", "seed", "demo", "fallback", "mock"}


def has_upcoming_registration(
    opportunity: Opportunity,
    now: Optional[datetime] = None,
) -> bool:
    """Only keep opportunities with a registration deadline still in the future.

    Event start/end dates are deliberately excluded: an event can be upcoming
    while registration has already closed, which would violate the Radar
    promise of showing only actionable opportunities.
    """

    if is_expired(opportunity, now):
        return False
    metadata = opportunity.decision_metadata or {}
    basis = str(metadata.get("deadline_basis") or "").strip().lower()
    # Legacy rows without provenance were already gated by the live pipeline.
    # Direct adapters always set a basis, so unknown bases are treated as event
    # dates rather than registration deadlines.
    return not basis or basis in _REGISTRATION_DEADLINE_BASES


def matches_persona(opportunity: Opportunity, persona: str) -> bool:
    """Global opportunities (no personas) match every persona."""
    personas = opportunity.domain_personas or []
    return not personas or persona in personas


def opportunity_bucket(opportunity: Opportunity) -> str:
    category = (opportunity.category or "").strip().lower()
    return "hackathon" if category in _HACKATHON_CATEGORIES else "general_event"


def _location_score(opportunity: Opportunity, city: Optional[str]) -> float:
    mode = (opportunity.location_type or "virtual").strip().lower()
    if mode in {"virtual", "online", "remote"}:
        return 1.0
    event_city = (opportunity.city or "").strip().lower()
    if not event_city:
        return 0.65
    if city and event_city == city.strip().lower():
        return 1.0
    return 0.25


def _urgency_score(opportunity: Opportunity, now: datetime) -> float:
    hours = (as_utc(opportunity.deadline) - now).total_seconds() / 3600.0
    if hours <= settings.URGENT_WINDOW_HOURS:
        return 1.0
    # Decay smoothly over a 30-day horizon.
    return max(0.15, 1.0 - min(hours - settings.URGENT_WINDOW_HOURS, 30 * 24) / (30 * 24))


def _vector_similarity(opportunity: Opportunity, dossier: Optional[ProjectDossier]) -> float:
    if dossier is None:
        return 0.0
    dossier_embedding = list(dossier.embedding or [])
    opportunity_embedding = list(opportunity.embedding or [])
    if not dossier_embedding or not opportunity_embedding:
        return 0.0
    return dedup_service.cosine_similarity(dossier_embedding, opportunity_embedding)


def score_opportunity(
    opportunity: Opportunity,
    persona: str,
    now: Optional[datetime] = None,
    dossier: Optional[ProjectDossier] = None,
    city: Optional[str] = None,
) -> float:
    """Deterministic 0..1 relevance score.

    Matches the product brief: ``0.5 * vector_similarity + 0.3 *
    city_or_online_match + 0.2 * deadline_urgency`` with a safe baseline for
    opportunities that do not have embeddings yet.
    """
    now = now or datetime.now(timezone.utc)
    similarity = _vector_similarity(opportunity, dossier)
    location = _location_score(opportunity, city)
    urgency = _urgency_score(opportunity, now)

    score = (0.5 * similarity) + (0.3 * location) + (0.2 * urgency)
    if similarity == 0.0:
        # Cold-start / not-yet-embedded events still deserve a usable ranking.
        score = 0.55 + (0.25 * location) + (0.20 * urgency)

    if persona in (opportunity.domain_personas or []):
        score += 0.03
    if opportunity.reward_pool:
        score += 0.01

    return round(min(0.99, max(0.35, score)), 2)


def why_you_match(
    opportunity: Opportunity,
    persona: str,
    dossier: Optional[ProjectDossier] = None,
) -> str:
    label = PERSONA_LABELS.get(persona, persona.replace("_", " ").title())
    host = opportunity.host_organization or "the host organization"
    project = dossier.title if dossier is not None else "your active proof-of-work"
    if opportunity.tags:
        tag_text = ", ".join(str(tag) for tag in opportunity.tags[:3])
        return (
            f"Selected by the {label} radar because {project} aligns with "
            f"{tag_text} and {host}'s evaluation focus."
        )
    return (
        f"Selected by the {label} radar for its strong fit with {project} "
        f"and {host}'s stated requirements."
    )


def networking_plan(
    opportunity: Opportunity,
    persona: str,
    dossier: Optional[ProjectDossier] = None,
    city: Optional[str] = None,
) -> NetworkingPlan:
    host = opportunity.host_organization or "Host"
    label = PERSONA_LABELS.get(persona, persona.replace("_", " ").title())
    project_title = dossier.title if dossier is not None else "our project"
    project_slug = dossier.slug if dossier is not None else "project"
    stack = ""
    if dossier is not None and dossier.tech_stack:
        stack = ", ".join(str(item) for item in dossier.tech_stack[:3])
    metric = ""
    if dossier is not None and dossier.key_metrics:
        first = dossier.key_metrics[0]
        if isinstance(first, dict):
            metric = f"{first.get('label', '')}: {first.get('value', '')}".strip(": ")

    project_url = f"https://studentradar.dev/p/{project_slug}"
    proof = f"{metric}; built with {stack}" if metric and stack else (metric or stack or project_title)
    where = f" in {city}" if city else ""

    starters = [
        (
            f"Hi — I saw {opportunity.title} and wanted to share how {project_title} "
            f"maps to the brief ({proof}). Open to a 10-minute walkthrough?"
        ),
        (
            f"Quick question on {opportunity.title}: our dossier documents {proof}. "
            f"Would a reproducible benchmark + public artifact be useful for your evaluation?"
        ),
    ]
    return NetworkingPlan(
        target_stakeholders=[
            f"Lead Evaluator at {host}",
            "Judging Panel Chair",
            "Program Manager / Partnerships Lead",
        ],
        pitch_angle=(
            f"Lead with verified benchmarks from {project_title} and a reproducible "
            f"artifact that maps directly to the {label} evaluation rubric."
        ),
        icebreaker_message=starters[0],
        conversation_starters=starters,
        followup_draft=(
            f"Hi — following up on {opportunity.title}{where}. Here is the full "
            f"proof-of-work dossier for {project_title}: {project_url}. Happy to "
            f"send the architecture notes or a short demo if useful."
        ),
    )


def to_opportunity_base(opportunity: Opportunity) -> OpportunityBase:
    deadline = as_utc(opportunity.deadline)
    return OpportunityBase(
        id=opportunity.id,
        title=opportunity.title,
        category=opportunity.category,
        canonical_source_url=opportunity.canonical_source_url,
        host_organization=opportunity.host_organization,
        organizer=opportunity.host_organization,
        deadline=deadline,
        deadline_at=deadline,
        city=opportunity.city,
        event_date=opportunity.event_date,
        description=opportunity.description,
        tags=opportunity.tags or [],
        domain_personas=opportunity.domain_personas or [],
        persona_tags=opportunity.domain_personas or [],
        location_type=opportunity.location_type or "virtual",
        mode=opportunity.location_type or "virtual",
        reward_pool=opportunity.reward_pool,
        decision_metadata=opportunity.decision_metadata or {},
    )


def build_briefing(
    opportunities: Iterable[Opportunity],
    persona: str,
    now: Optional[datetime] = None,
    dossier: Optional[ProjectDossier] = None,
    city: Optional[str] = None,
    briefing_type: str = "daily",
) -> RadarBriefingResponse:
    now = now or datetime.now(timezone.utc)

    pool = list(opportunities)
    active = [
        opportunity
        for opportunity in pool
        if is_radar_ready(opportunity)
        and has_upcoming_registration(opportunity, now)
        and matches_persona(opportunity, persona)
    ]
    # If a persona has no matching events yet, fall back only to global
    # opportunities (empty persona_tags). Showing another domain's events would
    # undermine the persona-specific radar promise.
    if not active:
        active = [
            opportunity
            for opportunity in pool
            if is_radar_ready(opportunity)
            and has_upcoming_registration(opportunity, now)
            and not (opportunity.domain_personas or [])
        ]

    ranked = sorted(
        active,
        key=lambda opportunity: (
            score_opportunity(opportunity, persona, now, dossier, city),
            -as_utc(opportunity.deadline).timestamp(),
        ),
        reverse=True,
    )

    urgent_deadlines: List[UrgentDeadline] = []
    for opportunity in ranked:
        hours_diff = int((as_utc(opportunity.deadline) - now).total_seconds() // 3600)
        if 0 < hours_diff <= settings.URGENT_WINDOW_HOURS:
            urgent_deadlines.append(
                UrgentDeadline(
                    id=opportunity.id,
                    title=opportunity.title,
                    category=opportunity.category,
                    deadline=as_utc(opportunity.deadline),
                    hours_remaining=hours_diff,
                    reward_pool=opportunity.reward_pool,
                )
            )

    strongest_pick: Optional[StrongestPick] = None
    if ranked:
        lead = ranked[0]
        lead_score = score_opportunity(lead, persona, now, dossier, city)
        base = to_opportunity_base(lead)
        strongest_pick = StrongestPick(
            **base.model_dump(),
            match_score=lead_score,
            why_you_match=why_you_match(lead, persona, dossier),
            networking_plan=networking_plan(lead, persona, dossier, city),
        )

    bases = [to_opportunity_base(opportunity) for opportunity in ranked]
    return RadarBriefingResponse(
        briefing_date=now.strftime("%Y-%m-%d"),
        briefing_type=briefing_type,
        persona=persona,
        urgent_deadlines=urgent_deadlines,
        strongest_pick=strongest_pick,
        hackathons=[
            base
            for base, opportunity in zip(bases, ranked)
            if opportunity_bucket(opportunity) == "hackathon"
        ],
        general_events=[
            base
            for base, opportunity in zip(bases, ranked)
            if opportunity_bucket(opportunity) == "general_event"
        ],
        all_opportunities=bases,
    )


def rank_opportunities(
    opportunities: Sequence[Opportunity],
    persona: str,
    now: Optional[datetime] = None,
    dossier: Optional[ProjectDossier] = None,
    city: Optional[str] = None,
) -> List[Tuple[Opportunity, float]]:
    now = now or datetime.now(timezone.utc)
    ranked = [
        (opportunity, score_opportunity(opportunity, persona, now, dossier, city))
        for opportunity in opportunities
        if not is_expired(opportunity, now)
    ]
    ranked.sort(key=lambda pair: (pair[1], as_utc(pair[0].deadline)), reverse=True)
    return ranked


radar_engine = type(
    "RadarEngine",
    (),
    {
        "build_briefing": staticmethod(build_briefing),
        "score_opportunity": staticmethod(score_opportunity),
        "matches_persona": staticmethod(matches_persona),
        "rank_opportunities": staticmethod(rank_opportunities),
        "opportunity_bucket": staticmethod(opportunity_bucket),
    },
)()
