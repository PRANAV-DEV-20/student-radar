import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import case, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.api.v1.auth import get_current_user_optional
from app.core.config import settings
from app.core.database import get_db
from app.models.dossier import ProjectDossier
from app.models.pr_reach import PRReachEvent
from app.models.user import User
from app.schemas.dossier import (
    DossierIngestRequest,
    DossierResponse,
    DossierVerifyResponse,
    RoadmapUpdateRequest,
)
from app.services.benchmark_scout import benchmark_scout
from app.services.ingestion_agent import ingestion_agent
from app.services.url_verifier import url_verifier

router = APIRouter(prefix="/dossiers", tags=["Project Dossiers"])

_GUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,100}$")
_URL_PATTERN = re.compile(r"https?://[^\s<>\"')]+", re.IGNORECASE)
_MAX_PDF_BYTES = 15 * 1024 * 1024

# Public dossier responses never expose embeddings. Keeping the vector columns
# out of these SELECTs avoids loading pgvector's shared library on read-only
# feed/detail requests, which also sidesteps stale GUC state on long-lived
# pooled connections.
_PUBLIC_DOSSIER_LOAD = (
    defer(ProjectDossier.embedding),
    defer(ProjectDossier.missing_roles_embedding),
)


def _guest_id(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if not _GUEST_ID_PATTERN.fullmatch(value):
        raise HTTPException(
            status_code=400,
            detail="X-Guest-Session-ID must be 1-100 characters of letters, digits, '.', '_', ':' or '-'.",
        )
    return value


def _extract_links(input_type: str, raw_content: str) -> Dict[str, str]:
    links: Dict[str, str] = {}
    for url in _URL_PATTERN.findall(raw_content or ""):
        url = url.rstrip(".,;)")
        lowered = url.lower()
        if "github.com" in lowered:
            links.setdefault("github", url)
        elif "figma.com" in lowered:
            links.setdefault("figma", url)
        elif any(token in lowered for token in (".pdf", "arxiv.org", "doi.org")):
            links.setdefault("paper", url)
        else:
            links.setdefault("demo", url)

    if input_type == "github" and "github" not in links:
        candidate = (raw_content or "").strip()
        if candidate.startswith(("http://", "https://")):
            links["github"] = candidate
    if input_type == "figma" and "figma" not in links:
        candidate = (raw_content or "").strip()
        if candidate.startswith(("http://", "https://")):
            links["figma"] = candidate
    return links


def _build_dossier(
    dossier_data: dict,
    req_persona: str,
    user_id,
    guest_id: Optional[str],
    links: Dict[str, str],
) -> ProjectDossier:
    return ProjectDossier(
        user_id=user_id,
        guest_session_id=guest_id,
        slug=dossier_data["slug"],
        title=dossier_data["title"],
        tagline=dossier_data["tagline"],
        domain_persona=req_persona,
        stage=dossier_data.get("stage") or "Prototype",
        problem_statement=dossier_data["problem_statement"],
        solution_breakdown=dossier_data["solution_breakdown"],
        tech_stack=dossier_data.get("tech_stack", []),
        key_metrics=dossier_data.get("key_metrics", []),
        whitespace_analysis=dossier_data.get("whitespace_analysis"),
        trend_radar_cache=dossier_data.get("trend_radar_cache"),
        benchmark_analysis=dossier_data.get("benchmark_analysis"),
        missing_roles=dossier_data.get("missing_roles", []),
        external_links=links,
        verified_status=False,
        embedding=dossier_data.get("embedding"),
        missing_roles_embedding=dossier_data.get("missing_roles_embedding"),
    )


async def _persist_new_dossier(
    dossier_data: dict,
    req_persona: str,
    current_user: Optional[User],
    guest_id: Optional[str],
    raw_content: str,
    input_type: str,
    db: AsyncSession,
) -> ProjectDossier:
    links = _extract_links(input_type, raw_content)
    new_dossier = _build_dossier(
        dossier_data=dossier_data,
        req_persona=req_persona,
        user_id=current_user.id if current_user else None,
        guest_id=None if current_user else guest_id,
        links=links,
    )
    db.add(new_dossier)
    await db.commit()
    await db.refresh(new_dossier)
    return new_dossier


@router.post("/ingest", response_model=DossierResponse, status_code=status.HTTP_201_CREATED)
async def ingest_artifact(
    req: DossierIngestRequest,
    x_guest_session_id: Optional[str] = Header(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Ingests an idea, GitHub repo, Figma link, or extracted PDF text, runs
    structured extraction + Trend Scout + embeddings, and returns a public
    Proof-of-Work Dossier.
    """
    guest_id = None if current_user else _guest_id(x_guest_session_id)

    dossier_data = await ingestion_agent.process_artifact(
        input_type="pdf_text" if req.input_type == "pdf" else req.input_type,
        raw_content=req.raw_content,
        domain_persona=req.domain_persona,
    )

    return await _persist_new_dossier(
        dossier_data=dossier_data,
        req_persona=req.domain_persona,
        current_user=current_user,
        guest_id=guest_id,
        raw_content=req.raw_content,
        input_type=req.input_type,
        db=db,
    )


@router.post(
    "/ingest-file",
    response_model=DossierResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a PDF dossier artifact",
)
async def ingest_pdf_file(
    file: UploadFile = File(..., description="Student PDF (max 15 MB)"),
    domain_persona: str = Form("tech_builder"),
    x_guest_session_id: Optional[str] = Header(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    guest_id = None if current_user else _guest_id(x_guest_session_id)
    persona = (domain_persona or settings.DEFAULT_PERSONA).strip().lower()
    if persona not in settings.KNOWN_PERSONAS:
        raise HTTPException(
            status_code=422,
            detail=(
                "Unsupported domain_persona. Choose one of: "
                + ", ".join(settings.KNOWN_PERSONAS)
            ),
        )

    content_type = (file.content_type or "").lower()
    filename = (file.filename or "").lower()
    if content_type not in {"application/pdf", "application/octet-stream"} and not filename.endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF uploads are supported.")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")
    if len(payload) > _MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF exceeds the 15 MB limit.")

    dossier_data = await ingestion_agent.process_pdf_bytes(
        payload, domain_persona=persona, filename=file.filename
    )

    return await _persist_new_dossier(
        dossier_data=dossier_data,
        req_persona=persona,
        current_user=current_user,
        guest_id=guest_id,
        raw_content=f"Uploaded PDF: {file.filename or 'document.pdf'}",
        input_type="pdf_text",
        db=db,
    )


@router.get("", response_model=List[DossierResponse])
async def list_dossiers(
    domain: Optional[str] = None,
    persona: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    # Active boosts first, then newest. Expired boosts lose their priority
    # automatically without needing a cleanup worker.
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    boost_rank = case(
        (
            ProjectDossier.boosted.is_(True)
            & ProjectDossier.boosted_until.is_not(None)
            & (ProjectDossier.boosted_until > now),
            0,
        ),
        else_=1,
    )
    query = (
        select(ProjectDossier)
        .options(*_PUBLIC_DOSSIER_LOAD)
        .order_by(boost_rank, desc(ProjectDossier.created_at))
        .offset(offset)
        .limit(limit)
    )
    selected_domain = domain or persona
    if selected_domain:
        query = query.where(ProjectDossier.domain_persona == selected_domain.strip().lower())

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{slug}", response_model=DossierResponse)
async def get_dossier(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProjectDossier)
        .where(ProjectDossier.slug == slug)
        .options(*_PUBLIC_DOSSIER_LOAD)
    )
    dossier = result.scalars().first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found.")
    return dossier


@router.get("/public/{slug}", response_model=DossierResponse)
async def get_public_dossier(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProjectDossier)
        .where(ProjectDossier.slug == slug)
        .options(*_PUBLIC_DOSSIER_LOAD)
    )
    dossier = result.scalars().first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found.")
    return dossier


@router.post("/{slug}/view", status_code=status.HTTP_204_NO_CONTENT)
async def record_dossier_view(
    slug: str,
    x_guest_session_id: Optional[str] = Header(default=None, alias="X-Guest-Session-ID"),
    db: AsyncSession = Depends(get_db),
):
    """Anonymous beacon fired by the public dossier page."""

    result = await db.execute(
        select(ProjectDossier)
        .where(ProjectDossier.slug == slug)
        .options(*_PUBLIC_DOSSIER_LOAD)
    )
    dossier = result.scalars().first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found.")

    db.add(
        PRReachEvent(
            dossier_id=dossier.id,
            event_type="dossier_view",
            event_metadata={"guest_session_id": x_guest_session_id, "source": "public_page"},
        )
    )
    await db.commit()
    return None


@router.post("/{id}/verify", response_model=DossierVerifyResponse)
async def verify_dossier_artifacts(id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProjectDossier)
        .where(ProjectDossier.id == id)
        .options(*_PUBLIC_DOSSIER_LOAD)
    )
    dossier = result.scalars().first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found.")

    links = dossier.external_links or {}
    checked, verified = await url_verifier.verify_links(links)

    dossier.verified_status = verified
    await db.commit()

    return DossierVerifyResponse(
        dossier_id=dossier.id,
        verified_status=verified,
        checked_urls=checked,
    )


async def _load_dossier_by_slug(slug: str, db: AsyncSession) -> ProjectDossier:
    result = await db.execute(
        select(ProjectDossier)
        .where(ProjectDossier.slug == slug)
        .options(*_PUBLIC_DOSSIER_LOAD)
    )
    dossier = result.scalars().first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found.")
    return dossier


@router.post("/{slug}/benchmark/refresh", response_model=DossierResponse)
async def refresh_ecosystem_benchmark(slug: str, db: AsyncSession = Depends(get_db)):
    """Re-run the two-tier Exa + Gemini benchmark for an existing dossier."""
    dossier = await _load_dossier_by_slug(slug, db)
    benchmark = await benchmark_scout.build_benchmark(
        {
            "title": dossier.title,
            "tagline": dossier.tagline,
            "problem_statement": dossier.problem_statement,
            "tech_stack": dossier.tech_stack or [],
            "domain_persona": dossier.domain_persona,
        }
    )
    previous = dossier.benchmark_analysis if isinstance(dossier.benchmark_analysis, dict) else {}
    if previous.get("selected_upgrades"):
        benchmark["selected_upgrades"] = previous["selected_upgrades"]
    dossier.benchmark_analysis = benchmark
    await db.commit()
    await db.refresh(dossier)
    return dossier


@router.post("/{slug}/roadmap", response_model=DossierResponse)
async def update_dossier_roadmap(
    slug: str,
    req: RoadmapUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Persist the upgrades a student selected for their 'What's Next' roadmap."""
    dossier = await _load_dossier_by_slug(slug, db)
    benchmark = dict(dossier.benchmark_analysis or {})
    benchmark["selected_upgrades"] = [item.model_dump() for item in req.selected_upgrades]
    benchmark.setdefault("similar_projects", [])
    benchmark.setdefault("advanced_upgrades", [])
    benchmark.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
    dossier.benchmark_analysis = benchmark
    await db.commit()
    await db.refresh(dossier)
    return dossier
