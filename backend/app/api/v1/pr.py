import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.dossier import ProjectDossier
from app.models.opportunity import Opportunity
from app.models.pr_asset import PRAsset
from app.models.pr_reach import PRReachEvent
from app.models.user import User
from app.schemas.pr import (
    PRBoostResponse,
    PRGenerateRequest,
    PRGenerateResponse,
    PRReachAnalyticsResponse,
    PRReachEventRequest,
)
from app.services.card_renderer import card_renderer
from app.services.credit_service import (
    ActiveBoostError,
    CreditError,
    InsufficientCreditsError,
    NotDossierOwnerError,
    credit_service,
)
from app.services.pr_strategist import pr_strategist

router = APIRouter(prefix="/pr", tags=["PR Studio"])


@router.post("/generate", response_model=PRGenerateResponse)
async def generate_pr_copy(req: PRGenerateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProjectDossier).where(ProjectDossier.id == req.dossier_id))
    dossier = result.scalars().first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found.")

    target_context: Optional[str] = req.target_opportunity_context
    if req.target_opportunity_id:
        opp_result = await db.execute(
            select(Opportunity).where(Opportunity.id == req.target_opportunity_id)
        )
        opportunity = opp_result.scalars().first()
        if not opportunity:
            raise HTTPException(status_code=404, detail="Target opportunity not found.")
        target_context = (
            (target_context or "")
            + f"\nTailor this pitch to: {opportunity.title} hosted by "
            f"{opportunity.host_organization or 'the organizer'}. "
            f"Brief: {opportunity.description}"
        ).strip()

    dossier_dict = {
        "id": str(dossier.id),
        "title": dossier.title,
        "tagline": dossier.tagline,
        "domain_persona": dossier.domain_persona,
        "stage": dossier.stage,
        "problem_statement": dossier.problem_statement,
        "solution_breakdown": dossier.solution_breakdown,
        "tech_stack": dossier.tech_stack,
        "key_metrics": dossier.key_metrics,
        "whitespace_analysis": dossier.whitespace_analysis,
        "trend_radar_cache": dossier.trend_radar_cache,
        "benchmark_analysis": dossier.benchmark_analysis,
        "missing_roles": dossier.missing_roles,
        "external_links": dossier.external_links,
        "slug": dossier.slug,
    }
    if target_context:
        dossier_dict["target_opportunity_context"] = target_context

    pr_result = await pr_strategist.generate_pr_assets(
        dossier=dossier_dict,
        playbook_type=req.playbook_type,
        tone=req.tone,
        target_audience=req.target_audience or "Engineers and Investors",
    )

    launch_card = card_renderer.generate_card_data_uri(dossier_dict)

    pr_asset = PRAsset(
        dossier_id=dossier.id,
        asset_type=req.playbook_type,
        content_json=pr_result,
        og_image_url=launch_card,
    )
    db.add(pr_asset)
    await db.commit()

    return PRGenerateResponse(
        asset_id=pr_asset.id,
        asset_type=req.playbook_type,
        platform=req.playbook_type,
        headline=pr_result.get("headline", ""),
        body_markdown=pr_result.get("body_markdown", ""),
        hooks=pr_result.get("hooks", []),
        suggested_tags=pr_result.get("suggested_tags", []),
        structured_payload=pr_result,
        og_image_url=launch_card,
        launch_card_url=launch_card,
    )


async def _boost(dossier_id: uuid.UUID, current_user: User, db: AsyncSession) -> PRBoostResponse:
    result = await db.execute(
        select(ProjectDossier)
        .where(ProjectDossier.id == dossier_id)
        .with_for_update()
    )
    dossier = result.scalars().first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found.")

    try:
        payload = await credit_service.boost_dossier(db, current_user, dossier)
        await db.commit()
    except InsufficientCreditsError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotDossierOwnerError as exc:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ActiveBoostError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except CreditError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PRBoostResponse(**payload)


@router.post("/{dossier_id}/boost", response_model=PRBoostResponse)
async def boost_dossier_feed(
    dossier_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _boost(dossier_id, current_user, db)


@router.post("/assets/{asset_id}/events", status_code=204)
async def record_pr_asset_event(
    asset_id: uuid.UUID,
    payload: PRReachEventRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Record an anonymous engagement event for a generated PR asset."""

    asset = await db.get(PRAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="PR asset not found.")

    metadata = dict(payload.metadata or {})
    metadata.setdefault("source", "pr_asset")
    db.add(
        PRReachEvent(
            dossier_id=asset.dossier_id,
            pr_asset_id=asset.id,
            event_type=payload.event_type,
            event_metadata={
                **metadata,
                "guest_session_id": payload.guest_session_id
                or request.headers.get("x-guest-session-id"),
            },
        )
    )
    await db.commit()
    return None


@router.get("/reach", response_model=PRReachAnalyticsResponse)
async def pr_reach_analytics(
    dossier_id: Optional[uuid.UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate real engagement events. No credits or fabricated impressions."""

    query = select(
        PRReachEvent.event_type,
        func.count(PRReachEvent.id),
        func.max(PRReachEvent.created_at),
    ).group_by(PRReachEvent.event_type)
    if dossier_id:
        query = query.where(PRReachEvent.dossier_id == dossier_id)

    rows = (await db.execute(query)).all()
    by_event_type: Dict[str, int] = {str(row[0]): int(row[1]) for row in rows}
    timestamps = [row[2] for row in rows if row[2] is not None]
    latest = max(timestamps) if timestamps else None
    if latest is not None and latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)

    return PRReachAnalyticsResponse(
        total=sum(by_event_type.values()),
        by_event_type=by_event_type,
        dossier_views=by_event_type.get("dossier_view", 0),
        asset_views=by_event_type.get("view", 0),
        latest_event_at=latest,
    )
