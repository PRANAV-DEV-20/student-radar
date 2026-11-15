from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class KeyMetric(BaseModel):
    label: str = Field(..., description="Short metric label, e.g. 'Latency' or 'Accuracy'")
    value: str = Field(..., description="Metric value, e.g. '12ms' or '99.4%'")

class MissingRole(BaseModel):
    role: str = Field(..., description="Target role name, e.g. 'Rust Embedded Engineer'")
    reason: str = Field(..., description="Why this role is needed to scale the project")

class WhitespaceAnalysis(BaseModel):
    market_gap: str = Field(..., description="Identified competitive whitespace or market bottleneck")
    top_voices: List[str] = Field(default_factory=list, description="Influential figures or labs in this domain")

class DossierIngestRequest(BaseModel):
    input_type: str = Field(..., description="'github' | 'idea' | 'pdf_text'")
    raw_content: str = Field(..., min_length=5, description="URL or raw text content of the project")
    domain_persona: str = Field(default="tech_builder", description="Domain persona key")

class DossierResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    guest_session_id: Optional[str] = None
    slug: str
    title: str
    tagline: str
    domain_persona: str
    problem_statement: str
    solution_breakdown: Dict[str, Any]
    tech_stack: List[str]
    key_metrics: List[KeyMetric]
    whitespace_analysis: Optional[WhitespaceAnalysis] = None
    missing_roles: List[MissingRole] = Field(default_factory=list)
    external_links: Dict[str, Any] = Field(default_factory=dict)
    verified_status: bool = False
    boosted: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DossierVerifyResponse(BaseModel):
    dossier_id: UUID
    verified_status: bool
    checked_urls: Dict[str, int]

