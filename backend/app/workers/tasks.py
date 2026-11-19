import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.briefing import UserBriefing
from app.models.dossier import ProjectDossier
from app.models.opportunity import Opportunity
from app.models.user import User
from app.services.opportunity_scout import opportunity_scout
from app.services.radar_engine import build_briefing
from app.services.signal_cache_service import refresh_all as refresh_signal_snapshots
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _session_factory():
    """A short-lived async engine per task keeps Celery loops isolated."""
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    return engine, session_factory


# ----------------------------------------------------------------------
# Opportunity scouting (5:30 AM IST)
# ----------------------------------------------------------------------
async def _crawl_opportunities():
    engine, session_factory = _session_factory()
    candidates = opportunity_scout.collect_candidates()
    try:
        async with session_factory() as db:
            result = await opportunity_scout.upsert(db, candidates)
            await db.commit()
        result.update(
            {
                "status": "success",
                "candidates_scouted": len(candidates),
            }
        )
        return result
    finally:
        await engine.dispose()


@celery_app.task(name="app.workers.tasks.crawl_and_deduplicate_opportunities")
def crawl_and_deduplicate_opportunities():
    """
    Scheduled 5:30 AM IST:
    1. Scoute live opportunities across all four PersonaConfigs.
    2. Pass 1 dedup: SHA-256 fingerprint / canonical URL.
    3. Pass 2 dedup: pgvector cosine similarity > 0.88 within a 3-day window.
    4. Merge cross-posted events or insert new rows.
    """
    logger.info("Executing 5:30 AM IST Opportunity Radar Crawl...")
    try:
        return asyncio.run(_crawl_opportunities())
    except Exception:
        logger.exception("Opportunity crawl failed.")
        raise


# ----------------------------------------------------------------------
# External signal cache (6:00 AM IST)
# ----------------------------------------------------------------------
async def _refresh_signal_cache():
    engine, session_factory = _session_factory()
    try:
        async with session_factory() as db:
            result = await refresh_signal_snapshots(db)
        result["status"] = "success"
        return result
    finally:
        await engine.dispose()


@celery_app.task(name="app.workers.tasks.refresh_signal_cache")
def refresh_signal_cache():
    """Refresh persisted market snapshots before the morning dashboard load."""

    logger.info("Executing 6:00 AM IST External Signal Cache Refresh...")
    try:
        return asyncio.run(_refresh_signal_cache())
    except Exception:
        logger.exception("External signal cache refresh failed.")
        raise


# ----------------------------------------------------------------------
# Daily / weekly briefings (7:00 AM IST / Sunday 6:00 PM IST)
# ----------------------------------------------------------------------
async def _compile_briefings(briefing_type: str):
    engine, session_factory = _session_factory()
    compiled = 0
    strongest_picks = 0
    email_jobs = []
    try:
        async with session_factory() as db:
            opportunities = list(
                (
                    await db.execute(
                        select(Opportunity).order_by(Opportunity.deadline.asc())
                    )
                )
                .scalars()
                .all()
            )
            users = list((await db.execute(select(User))).scalars().all())
            today = datetime.now(timezone.utc).date()

            for user in users:
                dossier_result = await db.execute(
                    select(ProjectDossier)
                    .where(ProjectDossier.user_id == user.id)
                    .order_by(ProjectDossier.created_at.desc())
                    .limit(1)
                )
                dossier = dossier_result.scalars().first()
                persona = user.active_persona_id or settings.DEFAULT_PERSONA

                briefing = build_briefing(
                    opportunities,
                    persona,
                    dossier=dossier,
                    city=user.city,
                    briefing_type=briefing_type,
                )

                urgent_ids = [str(item.id) for item in briefing.urgent_deadlines]
                strongest_pick_id = None
                rationale = None
                networking_plan = None
                if briefing.strongest_pick is not None:
                    strongest_pick_id = briefing.strongest_pick.id
                    rationale = briefing.strongest_pick.why_you_match
                    networking_plan = briefing.strongest_pick.networking_plan.model_dump(
                        mode="json"
                    )
                    pick_id = str(strongest_pick_id)
                    if pick_id not in urgent_ids:
                        urgent_ids.append(pick_id)
                    strongest_picks += 1

                payload = {
                    "dossier_id": dossier.id if dossier else None,
                    "opportunity_ids": urgent_ids,
                    "strongest_pick_id": strongest_pick_id,
                    "strongest_pick_rationale": rationale,
                    "networking_plan_json": networking_plan,
                    "ranked_hackathons": [
                        item.model_dump(mode="json") for item in briefing.hackathons
                    ],
                    "ranked_events": [
                        item.model_dump(mode="json") for item in briefing.general_events
                    ],
                    "persona_mode": persona,
                }

                existing_result = await db.execute(
                    select(UserBriefing).where(
                        UserBriefing.user_id == user.id,
                        UserBriefing.briefing_date == today,
                        UserBriefing.briefing_type == briefing_type,
                    )
                )
                existing = existing_result.scalars().first()
                if existing:
                    for key, value in payload.items():
                        setattr(existing, key, value)
                else:
                    db.add(
                        UserBriefing(
                            user_id=user.id,
                            briefing_date=today,
                            briefing_type=briefing_type,
                            **payload,
                        )
                    )
                compiled += 1
                email_jobs.append((str(user.id), today.isoformat()))

            await db.commit()

        if settings.ENABLE_CELERY_DISPATCH:
            for user_id, briefing_date in email_jobs:
                try:
                    await asyncio.to_thread(
                        send_briefing_email.delay,
                        user_id,
                        briefing_type,
                        briefing_date,
                    )
                except Exception as exc:  # pragma: no cover - broker optional
                    logger.warning("Could not dispatch briefing email task: %s", exc)

        return {
            "status": "success",
            "briefing_type": briefing_type,
            "briefings_compiled": compiled,
            "with_strongest_pick": strongest_picks,
            "emails_queued": len(email_jobs) if settings.ENABLE_CELERY_DISPATCH else 0,
        }
    finally:
        await engine.dispose()


@celery_app.task(name="app.workers.tasks.compile_daily_user_briefings")
def compile_daily_user_briefings():
    """
    Scheduled 7:00 AM IST:
    Rank opportunities per active persona, compute the strongest pick, build a
    project-aware networking plan, and persist the daily briefing.
    """
    logger.info("Executing 7:00 AM IST Daily Briefing Compilation...")
    try:
        return asyncio.run(_compile_briefings("daily"))
    except Exception:
        logger.exception("Daily briefing compilation failed.")
        raise


@celery_app.task(name="app.workers.tasks.compile_weekly_user_briefings")
def compile_weekly_user_briefings():
    """Scheduled Sunday 6:00 PM IST: weekly strongest-pick briefing."""
    logger.info("Executing Sunday 6:00 PM IST Weekly Briefing Compilation...")
    try:
        return asyncio.run(_compile_briefings("weekly"))
    except Exception:
        logger.exception("Weekly briefing compilation failed.")
        raise


# ----------------------------------------------------------------------
# Outbound notifications (provider-agnostic stubs)
# ----------------------------------------------------------------------
@celery_app.task(name="app.workers.tasks.send_invite_email")
def send_invite_email(recipient_email_hash: str, invite_token: str, project_title: str):
    """Asynchronous invite dispatch hook.

    No raw email address is ever passed to the worker; production deployments
    can plug an ESP here using the recipient hash only for idempotency.
    """
    logger.info(
        "Dispatching project invite (hash=%s..., token=%s, project=%s)",
        recipient_email_hash[:10],
        invite_token,
        project_title,
    )
    return {"status": "dispatched"}


@celery_app.task(name="app.workers.tasks.send_briefing_email")
def send_briefing_email(user_id: str, briefing_type: str, briefing_date: str):
    """Asynchronous briefing digest dispatch hook."""
    logger.info(
        "Dispatching %s briefing for user=%s on %s",
        briefing_type,
        user_id,
        briefing_date,
    )
    return {"status": "dispatched"}
