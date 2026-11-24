"""Dossier v2 API: background research runs, SSE progress and grounded tools."""
from __future__ import annotations

import asyncio
import json
import re
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Response,
    status,
)
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user_optional
from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.models.dossier_v2 import (
    AIRun,
    DossierRun,
    DossierSection,
    DossierVersion,
    Evidence,
    SectionReview,
)
from app.models.user import User
from app.schemas.dossier_v2 import (
    SECTION_KEYS,
    ChatRequest,
    DeepenRequest,
    RoadmapRequest,
    RunCreateRequest,
    SectionPatch,
    validate_section_payload,
)
from app.services.dossier_v2_events import event_store
from app.services.dossier_v2_pipeline import DossierPipeline, export_markdown

router = APIRouter(prefix="/dossiers/v2", tags=["Dossier v2 Research"])

_GUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,100}$")


def _guest_id(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if not _GUEST_ID_PATTERN.fullmatch(value):
        raise HTTPException(status_code=400, detail="Invalid X-Guest-Session-ID")
    return value


async def _run_emitter(run_id: uuid.UUID):
    async def emit(event_type: str, data: Dict[str, Any]) -> None:
        await event_store.publish(run_id, event_type, data)
    return emit


async def _launch(run_id: uuid.UUID) -> None:
    pipeline = DossierPipeline(run_id, await _run_emitter(run_id))
    await pipeline.execute()
    await event_store.close(run_id)


async def _launch_deepen(run_id: uuid.UUID, section: str) -> None:
    pipeline = DossierPipeline(run_id, await _run_emitter(run_id))
    await pipeline.deepen(section)


def _error_state(run: DossierRun) -> Optional[Dict[str, Any]]:
    if not run.error:
        return None
    try:
        return json.loads(run.error)
    except json.JSONDecodeError:
        return {"code": "PIPELINE_FAILED", "message": run.error}


async def _state(run: DossierRun, db: AsyncSession) -> Dict[str, Any]:
    sections = {
        row.section: {**row.content, "locked": bool(row.locked)}
        for row in (await db.execute(
            select(DossierSection).where(DossierSection.run_id == run.id)
        )).scalars()
    }
    evidence_rows = (await db.execute(select(Evidence).where(Evidence.run_id == run.id))).scalars().all()
    evidence = [
        {
            "ref": row.ref, "question_id": row.question_id, "url": row.url,
            "title": row.title, "source": row.source, "source_quality": row.source_quality,
            "passage": row.passage, "relevance": row.relevance,
            "retrieved_at": row.retrieved_at.isoformat() if row.retrieved_at else None,
        }
        for row in evidence_rows
    ]
    reviews = [
        {
            "section": row.section, "attempt": row.attempt, "passed": row.passed,
            "failures": row.failures,
        }
        for row in (await db.execute(
            select(SectionReview).where(SectionReview.run_id == run.id).order_by(SectionReview.section, SectionReview.attempt)
        )).scalars()
    ]
    ai_runs = [
        {
            "id": str(row.id), "role": row.role, "model": row.model, "success": bool(row.success),
            "prompt_tokens": row.prompt_tokens, "output_tokens": row.output_tokens,
            "total_tokens": row.total_tokens, "latency_ms": row.latency_ms,
            "attempts": row.attempts, "fallback_used": bool(row.fallback_used),
            "cached": bool(row.cached), "cost_usd": float(row.cost_usd or 0),
            "error": row.error,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in (await db.execute(
            select(AIRun).where(AIRun.run_id == run.id).order_by(AIRun.created_at)
        )).scalars()
    ]
    versions = [
        {
            "version": row.version,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "sections": list((row.snapshot or {}).get("sections") or {}),
        }
        for row in (await db.execute(
            select(DossierVersion).where(DossierVersion.run_id == run.id).order_by(DossierVersion.version)
        )).scalars()
    ]
    return {
        "id": str(run.id),
        "project_id": str(run.project_id) if run.project_id else None,
        "status": run.status,
        "mode": run.mode,
        "input_type": run.input_type,
        "domain_persona": run.domain_persona,
        "progress": run.progress or {},
        "plan": run.plan,
        "coverage": run.coverage,
        "profile": run.profile,
        "tasks": run.tasks or [],
        "sections": sections,
        "evidence": evidence,
        "reviews": reviews,
        "ai_runs": ai_runs,
        "versions": versions,
        "error": _error_state(run),
        "cost_usd": float(run.cost_usd or 0),
        "duration_ms": run.duration_ms,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


async def _get_run(run_id: uuid.UUID, db: AsyncSession) -> DossierRun:
    run = await db.get(DossierRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Dossier run not found.")
    return run


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
async def create_run(
    req: RunCreateRequest,
    x_guest_session_id: Optional[str] = Header(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Start a real research run. No provider key means a 503, never template text."""
    if not settings.llm_configured:
        return JSONResponse(
            status_code=503,
            content={
                "detail": {
                    "code": "AI_PROVIDER_NOT_CONFIGURED",
                    "message": "AI provider not configured. Set GEMINI_API_KEY or GROQ_API_KEY to generate a Dossier v2. "
                               "Deterministic template output is disabled by design.",
                }
            },
        )
    run = DossierRun(
        user_id=current_user.id if current_user else None,
        guest_session_id=None if current_user else _guest_id(x_guest_session_id),
        status="queued",
        mode=req.mode,
        input_type=req.input_type,
        raw_content=req.raw_content,
        domain_persona=req.domain_persona,
        profile=req.profile.model_dump(),
        progress={"stage": "queued", "message": "Queued", "completed_sections": 0, "total_sections": len(SECTION_KEYS)},
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    asyncio.create_task(_launch(run.id))
    return {
        "run_id": str(run.id),
        "status": run.status,
        "stream_url": f"/api/v1/dossiers/v2/runs/{run.id}/events",
    }


@router.get("/runs/{run_id}")
async def get_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await _state(await _get_run(run_id, db), db)


@router.get("/runs/{run_id}/events")
async def stream_events(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await _get_run(run_id, db)

    async def generator() -> AsyncGenerator[str, None]:
        history, queue, channel = event_store.subscribe(run_id)
        try:
            for event in history:
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event.get("type") in {"complete", "error"}:
                    break
            if channel.closed:
                return
        finally:
            if queue in channel.subscribers:
                channel.subscribers.remove(queue)

    return StreamingResponse(generator(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


@router.post("/runs/{run_id}/deepen", status_code=202)
async def deepen_section(run_id: uuid.UUID, req: DeepenRequest, db: AsyncSession = Depends(get_db)):
    run = await _get_run(run_id, db)
    if run.status not in {"succeeded", "partial"}:
        raise HTTPException(status_code=409, detail="Only a finished run can be deepened.")
    if not settings.llm_configured:
        raise HTTPException(status_code=503, detail="AI provider not configured")
    asyncio.create_task(_launch_deepen(run_id, req.section))
    return {"run_id": str(run_id), "section": req.section, "status": "deepening"}


@router.post("/runs/{run_id}/chat")
async def chat_about_dossier(run_id: uuid.UUID, req: ChatRequest, db: AsyncSession = Depends(get_db)):
    await _get_run(run_id, db)
    pipeline = DossierPipeline(run_id, await _run_emitter(run_id))
    return await pipeline.chat(req.question)


@router.patch("/runs/{run_id}/sections/{section}")
async def patch_section(
    run_id: uuid.UUID,
    section: str,
    req: SectionPatch,
    db: AsyncSession = Depends(get_db),
):
    if section not in SECTION_KEYS:
        raise HTTPException(status_code=404, detail="Unknown section")
    row = (await db.execute(
        select(DossierSection).where(DossierSection.run_id == run_id, DossierSection.section == section)
    )).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Section not found in this run")
    refs = {
        item.ref for item in (await db.execute(
            select(Evidence.ref).where(Evidence.run_id == run_id)
        )).scalars()
    }
    try:
        content = validate_section_payload(req.content, section, refs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    row.content = content
    row.locked = req.locked
    row.confidence = content.get("confidence", row.confidence)
    row.coverage = content.get("coverage", row.coverage)
    await db.commit()
    return {"section": section, "content": content, "locked": row.locked}


@router.post("/runs/{run_id}/rerun", status_code=202)
async def rerun(
    run_id: uuid.UUID,
    x_guest_session_id: Optional[str] = Header(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    old = await _get_run(run_id, db)
    if not settings.llm_configured:
        raise HTTPException(status_code=503, detail="AI provider not configured")
    run = DossierRun(
        user_id=current_user.id if current_user else None,
        guest_session_id=None if current_user else _guest_id(x_guest_session_id),
        status="queued",
        mode=old.mode,
        input_type=old.input_type,
        raw_content=old.raw_content,
        domain_persona=old.domain_persona,
        profile=dict(old.profile or {}),
        progress={"stage": "queued", "message": "Queued re-run with changes tracked", "completed_sections": 0,
                  "total_sections": len(SECTION_KEYS)},
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    asyncio.create_task(_launch(run.id))
    return {"run_id": str(run.id), "status": "queued", "previous_run_id": str(run_id)}


@router.post("/runs/{run_id}/roadmap")
async def add_to_roadmap(run_id: uuid.UUID, req: RoadmapRequest, db: AsyncSession = Depends(get_db)):
    run = await _get_run(run_id, db)
    tasks = list(run.tasks or [])
    tasks.extend(item.model_dump() for item in req.items)
    run.tasks = tasks[-60:]
    section_row = (await db.execute(
        select(DossierSection).where(DossierSection.run_id == run_id, DossierSection.section == "roadmap")
    )).scalars().first()
    if section_row:
        content = dict(section_row.content or {})
        items = list(content.get("items") or [])
        for index, item in enumerate(req.items, start=len(items) + 1):
            items.append({
                "id": f"T{index}",
                "label": "recommendation",
                "text": item.text,
                "evidence": [],
                "effort": item.effort,
                "reasoning": f"Added from {item.section}; it addresses a gap or risk in this dossier.",
            })
        content["items"] = items[-40:]
        section_row.content = content
    await db.commit()
    return {"run_id": str(run_id), "tasks": run.tasks}


@router.get("/runs/{run_id}/diff")
async def diff_versions(
    run_id: uuid.UUID,
    from_version: int = Query(1, alias="from", ge=1),
    to_version: int = Query(2, alias="to", ge=1),
    db: AsyncSession = Depends(get_db),
):
    """Show which sections changed between two persisted snapshots."""
    await _get_run(run_id, db)
    rows = (await db.execute(
        select(DossierVersion).where(DossierVersion.run_id == run_id).order_by(DossierVersion.version)
    )).scalars().all()
    versions = {row.version: row for row in rows}
    if from_version not in versions or to_version not in versions:
        raise HTTPException(status_code=404, detail="Requested version snapshot not found")
    before = (versions[from_version].snapshot or {}).get("sections") or {}
    after = (versions[to_version].snapshot or {}).get("sections") or {}
    changed = [key for key in SECTION_KEYS if before.get(key) != after.get(key)]
    return {
        "run_id": str(run_id),
        "from": from_version,
        "to": to_version,
        "changed_sections": changed,
        "before": {key: before.get(key) for key in changed},
        "after": {key: after.get(key) for key in changed},
    }


@router.get("/runs/{run_id}/export")
async def export_dossier(
    run_id: uuid.UUID,
    format: str = Query("markdown", pattern="^(markdown|json)$"),
    db: AsyncSession = Depends(get_db),
):
    state = await _state(await _get_run(run_id, db), db)
    if format == "json":
        return Response(
            content=json.dumps(state, ensure_ascii=False, default=str, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="dossier-v2-{run_id}.json"'},
        )
    return PlainTextResponse(
        content=export_markdown(state["sections"]),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="dossier-v2-{run_id}.md"'},
    )
