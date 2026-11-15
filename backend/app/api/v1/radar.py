import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.opportunity import Opportunity
from app.schemas.radar import (
    RadarBriefingResponse,
    OpportunityBase,
    StrongestPick,
    UrgentDeadline,
    NetworkingPlan
)
from app.services.calendar_service import calendar_service

router = APIRouter(prefix="/radar", tags=["Opportunity Radar"])

@router.get("/briefing", response_model=RadarBriefingResponse)
async def get_radar_briefing(
    persona: str = "tech_builder",
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Opportunity).order_by(Opportunity.deadline.asc()))
    all_opps = result.scalars().all()

    # Filter opportunities matching persona
    matching_opps = [
        o for o in all_opps 
        if persona in (o.domain_personas or []) or not o.domain_personas
    ]
    if not matching_opps:
        matching_opps = all_opps # fallback to all if empty

    now = datetime.now(timezone.utc)
    urgent_deadlines = []
    for opp in matching_opps:
        hours_diff = int((opp.deadline - now).total_seconds() / 3600)
        if 0 < hours_diff <= 168: # within 7 days
            urgent_deadlines.append(
                UrgentDeadline(
                    id=opp.id,
                    title=opp.title,
                    category=opp.category,
                    deadline=opp.deadline,
                    hours_remaining=hours_diff,
                    reward_pool=opp.reward_pool
                )
            )

    # Designate the Strongest Pick
    strongest_pick = None
    if matching_opps:
        lead = matching_opps[0]
        strongest_pick = StrongestPick(
            id=lead.id,
            title=lead.title,
            category=lead.category,
            canonical_source_url=lead.canonical_source_url,
            host_organization=lead.host_organization,
            deadline=lead.deadline,
            description=lead.description,
            tags=lead.tags or [],
            domain_personas=lead.domain_personas or [],
            location_type=lead.location_type or "virtual",
            reward_pool=lead.reward_pool,
            match_score=0.96,
            why_you_match="High alignment with your technical stack, latency metrics, and decentralized architecture benchmarks.",
            networking_plan=NetworkingPlan(
                target_stakeholders=[
                    f"Lead Evaluator at {lead.host_organization or 'Host'}",
                    "Judging Panel Chair"
                ],
                pitch_angle="Focus on verified benchmarks (< 15ms latency) and open-source reproducibility.",
                icebreaker_message=f"Hi, we saw the call for {lead.title}. We've built an open-source decentralized orchestrator that meets these exact requirements."
            )
        )

    opportunity_bases = [
        OpportunityBase(
            id=o.id,
            title=o.title,
            category=o.category,
            canonical_source_url=o.canonical_source_url,
            host_organization=o.host_organization,
            deadline=o.deadline,
            description=o.description,
            tags=o.tags or [],
            domain_personas=o.domain_personas or [],
            location_type=o.location_type or "virtual",
            reward_pool=o.reward_pool
        )
        for o in matching_opps
    ]

    return RadarBriefingResponse(
        briefing_date=now.strftime("%Y-%m-%d"),
        persona=persona,
        urgent_deadlines=urgent_deadlines,
        strongest_pick=strongest_pick,
        all_opportunities=opportunity_bases
    )

@router.get("/opportunities", response_model=List[OpportunityBase])
async def list_opportunities(
    persona: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Opportunity).order_by(Opportunity.deadline.asc())
    result = await db.execute(query)
    opps = result.scalars().all()

    if persona:
        opps = [o for o in opps if persona in (o.domain_personas or [])]
    if category:
        opps = [o for o in opps if o.category.lower() == category.lower()]

    return [
        OpportunityBase(
            id=o.id,
            title=o.title,
            category=o.category,
            canonical_source_url=o.canonical_source_url,
            host_organization=o.host_organization,
            deadline=o.deadline,
            description=o.description,
            tags=o.tags or [],
            domain_personas=o.domain_personas or [],
            location_type=o.location_type or "virtual",
            reward_pool=o.reward_pool
        )
        for o in opps
    ]

@router.get("/{id}/ics")
async def download_calendar_event(id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Opportunity).where(Opportunity.id == id))
    opp = result.scalars().first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found.")

    ics_data = calendar_service.generate_ics(
        title=opp.title,
        description=opp.description,
        deadline=opp.deadline,
        url=opp.canonical_source_url,
        host_organization=opp.host_organization
    )

    filename = f"radar-event-{opp.id}.ics"
    return Response(
        content=ics_data,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

