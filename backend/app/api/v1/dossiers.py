import uuid
import httpx
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_db
from app.models.user import User
from app.models.dossier import ProjectDossier
from app.schemas.dossier import (
    DossierIngestRequest,
    DossierResponse,
    DossierVerifyResponse
)
from app.services.ingestion_agent import ingestion_agent
from app.api.v1.auth import get_current_user_optional

router = APIRouter(prefix="/dossiers", tags=["Project Dossiers"])

@router.post("/ingest", response_model=DossierResponse, status_code=status.HTTP_201_CREATED)
async def ingest_artifact(
    req: DossierIngestRequest,
    x_guest_session_id: Optional[str] = Header(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingests an idea, GitHub repo, or PDF text, runs Gemini structured extraction,
    and returns an Editorial Proof-of-Work Dossier in <3 seconds.
    """
    dossier_data = await ingestion_agent.process_artifact(
        input_type=req.input_type,
        raw_content=req.raw_content,
        domain_persona=req.domain_persona
    )

    user_id = current_user.id if current_user else None
    guest_id = x_guest_session_id if not user_id else None

    # Detect external links
    external_links = {}
    if req.input_type == "github" and "github.com" in req.raw_content:
        external_links["github"] = req.raw_content.strip()

    new_dossier = ProjectDossier(
        user_id=user_id,
        guest_session_id=guest_id,
        slug=dossier_data["slug"],
        title=dossier_data["title"],
        tagline=dossier_data["tagline"],
        domain_persona=req.domain_persona,
        problem_statement=dossier_data["problem_statement"],
        solution_breakdown=dossier_data["solution_breakdown"],
        tech_stack=dossier_data["tech_stack"],
        key_metrics=dossier_data["key_metrics"],
        whitespace_analysis=dossier_data.get("whitespace_analysis"),
        missing_roles=dossier_data.get("missing_roles", []),
        external_links=external_links,
        verified_status=bool(external_links),
        embedding=dossier_data.get("embedding")
    )

    db.add(new_dossier)
    await db.commit()
    await db.refresh(new_dossier)

    return new_dossier

@router.get("", response_model=List[DossierResponse])
async def list_dossiers(
    domain: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    query = select(ProjectDossier).order_by(desc(ProjectDossier.boosted), desc(ProjectDossier.created_at))
    if domain:
        query = query.where(ProjectDossier.domain_persona == domain)
    result = await db.execute(query.limit(limit))
    return result.scalars().all()

@router.get("/{slug}", response_model=DossierResponse)
async def get_dossier(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProjectDossier).where(ProjectDossier.slug == slug))
    dossier = result.scalars().first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found.")
    return dossier

@router.get("/public/{slug}", response_model=DossierResponse)
async def get_public_dossier(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProjectDossier).where(ProjectDossier.slug == slug))
    dossier = result.scalars().first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found.")
    return dossier

@router.post("/{id}/verify", response_model=DossierVerifyResponse)
async def verify_dossier_artifacts(id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProjectDossier).where(ProjectDossier.id == id))
    dossier = result.scalars().first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found.")

    links = dossier.external_links or {}
    checked = {}
    verified = False

    async with httpx.AsyncClient(timeout=5.0) as client:
        for key, url in links.items():
            try:
                resp = await client.head(url, follow_redirects=True)
                checked[key] = resp.status_code
                if resp.status_code == 200:
                    verified = True
            except Exception:
                checked[key] = 0

    dossier.verified_status = verified
    await db.commit()

    return DossierVerifyResponse(
        dossier_id=dossier.id,
        verified_status=verified,
        checked_urls=checked
    )

