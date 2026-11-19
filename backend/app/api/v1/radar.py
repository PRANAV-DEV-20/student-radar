import uuid
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user, get_current_user_optional
from app.core.config import settings
from app.core.database import get_db
from app.models.dossier import ProjectDossier
from app.models.opportunity import Opportunity
from app.models.user import User
from app.schemas.radar import (
    OpportunityBase,
    RadarBriefingResponse,
    ReprofileRequest,
    ReprofileResponse,
    ScanLiveRequest,
    ScanLiveResponse,
)
from app.services.calendar_service import calendar_service
from app.services.radar_engine import (
    build_briefing,
    matches_persona,
    opportunity_bucket,
    to_opportunity_base,
)
from app.services.radar_live_service import scan_live as run_live_scan

router = APIRouter(prefix="/radar", tags=["Opportunity Radar"])


async def _resolve_context(
    db: AsyncSession,
    current_user: Optional[User],
    dossier_id: Optional[uuid.UUID],
    dossier_slug: Optional[str],
) -> Optional[ProjectDossier]:
    if dossier_id:
        result = await db.execute(select(ProjectDossier).where(ProjectDossier.id == dossier_id))
        return result.scalars().first()
    if dossier_slug:
        result = await db.execute(select(ProjectDossier).where(ProjectDossier.slug == dossier_slug))
        return result.scalars().first()
    if current_user:
        result = await db.execute(
            select(ProjectDossier)
            .where(ProjectDossier.user_id == current_user.id)
            .order_by(ProjectDossier.created_at.desc())
            .limit(1)
        )
        return result.scalars().first()
    return None


async def _all_opportunities(db: AsyncSession) -> List[Opportunity]:
    result = await db.execute(select(Opportunity).order_by(Opportunity.deadline.asc()))
    return list(result.scalars().all())


@router.get("/briefing", response_model=RadarBriefingResponse)
async def get_radar_briefing(
    persona: Optional[str] = Query(default=None),
    briefing_type: Literal["daily", "weekly"] = Query(default="daily"),
    dossier_id: Optional[uuid.UUID] = Query(default=None),
    dossier_slug: Optional[str] = Query(default=None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    resolved_persona = (
        persona
        or (current_user.active_persona_id if current_user else None)
        or settings.DEFAULT_PERSONA
    ).strip().lower()
    if resolved_persona not in settings.KNOWN_PERSONAS:
        raise HTTPException(
            status_code=422,
            detail="Unknown persona. Expected one of: " + ", ".join(settings.KNOWN_PERSONAS),
        )

    dossier = await _resolve_context(db, current_user, dossier_id, dossier_slug)
    city = current_user.city if current_user else None
    opportunities = await _all_opportunities(db)

    return build_briefing(
        opportunities,
        resolved_persona,
        dossier=dossier,
        city=city,
        briefing_type=briefing_type,
    )


@router.post("/scan-live", response_model=ScanLiveResponse)
async def scan_live_radar(
    req: ScanLiveRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Generate intent queries, gatekeep + rerank live results, and refresh the feed.

    This is the on-demand counterpart to the scheduled Celery digest. It never
    uses a cached snapshot (``max_age_hours=0`` by default) and never fabricates
    an event, deadline, reward, or metric.
    """

    # A typed idea is authoritative. Only fall back to the persisted dossier
    # when the user did not supply fresh input on this scan.
    typed_idea = (req.raw_idea or "").strip()
    dossier = None if typed_idea else await _resolve_context(
        db, current_user, req.dossier_id, req.dossier_slug
    )
    if dossier is None and not typed_idea:
        raise HTTPException(
            status_code=422,
            detail="Provide a dossier_id, dossier_slug, or raw_idea to scan.",
        )

    result = await run_live_scan(
        db=db,
        dossier=dossier,
        raw_idea=req.raw_idea,
        persona=req.persona,
        intents=req.intents,
        language=req.language,
        max_age_hours=req.max_age_hours,
    )
    return result


@router.post("/reprofile", response_model=ReprofileResponse)
async def reprofile_radar(
    req: ReprofileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Switch the user's active PersonaConfig and immediately refresh the feed."""
    current_user.active_persona_id = req.persona_id
    await db.commit()
    await db.refresh(current_user)

    dossier = await _resolve_context(db, current_user, None, None)
    opportunities = await _all_opportunities(db)
    briefing = build_briefing(
        opportunities,
        req.persona_id,
        dossier=dossier,
        city=current_user.city,
        briefing_type="daily",
    )
    return ReprofileResponse(
        status="updated",
        persona=req.persona_id,
        active_persona_id=current_user.active_persona_id,
        briefing=briefing,
    )


@router.get("/opportunities", response_model=List[OpportunityBase])
async def list_opportunities(
    persona: Optional[str] = None,
    category: Optional[str] = None,
    city: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    opportunities = await _all_opportunities(db)
    if persona:
        opportunities = [opp for opp in opportunities if matches_persona(opp, persona)]
    if category:
        requested = category.strip().lower()
        if requested in {"hackathon", "hackathons", "build_sprint", "build_sprints"}:
            opportunities = [
                opp for opp in opportunities if opportunity_bucket(opp) == "hackathon"
            ]
        elif requested in {"general_event", "general_events", "event", "events"}:
            opportunities = [
                opp for opp in opportunities if opportunity_bucket(opp) == "general_event"
            ]
        else:
            opportunities = [
                opp for opp in opportunities if (opp.category or "").lower() == requested
            ]
    if city:
        city_lower = city.strip().lower()
        opportunities = [
            opp
            for opp in opportunities
            if (opp.location_type or "").lower() in {"virtual", "online", "remote"}
            or (opp.city or "").strip().lower() == city_lower
        ]
    return [to_opportunity_base(opp) for opp in opportunities]


@router.get("/{id}/ics")
async def download_calendar_event(id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Opportunity).where(Opportunity.id == id))
    opportunity = result.scalars().first()
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found.")

    ics_data = calendar_service.generate_ics(
        title=opportunity.title,
        description=opportunity.description,
        deadline=opportunity.deadline,
        url=opportunity.canonical_source_url,
        host_organization=opportunity.host_organization,
        event_id=str(opportunity.id),
    )

    filename = f"radar-event-{opportunity.id}.ics"
    return Response(
        content=ics_data,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
