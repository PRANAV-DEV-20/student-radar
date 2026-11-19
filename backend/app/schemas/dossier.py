import re
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings

_PERSONA_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,49}$")


class KeyMetric(BaseModel):
    label: str = Field(..., description="Short metric label, e.g. 'Latency' or 'Accuracy'")
    value: str = Field(..., description="Metric value, e.g. '12ms' or '99.4%'")


class MissingRole(BaseModel):
    role: str = Field(..., description="Target role name, e.g. 'Rust Embedded Engineer'")
    reason: str = Field(..., description="Why this role is needed to scale the project")


class WhitespaceAnalysis(BaseModel):
    market_gap: str = Field(..., description="Identified competitive whitespace or market bottleneck")
    top_voices: List[str] = Field(default_factory=list, description="Influential figures or labs in this domain")


class SimilarProject(BaseModel):
    name: str = Field(..., description="Peer project name")
    source_platform: str = Field(..., description="Platform or host, e.g. GitHub")
    url: str = Field(..., description="Real, openable source URL")
    what_they_built: str = Field(default="", description="Grounded one-line summary")
    student_differentiator: str = Field(
        default="",
        description="Honest differentiation grounded in the submitted dossier; empty when unsupported",
    )

    @field_validator("name", mode="before")
    @classmethod
    def cap_name(cls, value: Any) -> str:
        return str(value or "")[:160]

    @field_validator("source_platform", mode="before")
    @classmethod
    def cap_source(cls, value: Any) -> str:
        return str(value or "")[:80]

    @field_validator("what_they_built", "student_differentiator", mode="before")
    @classmethod
    def cap_summary(cls, value: Any) -> str:
        return str(value or "")[:600]

    @field_validator("url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        value = (value or "").strip()
        if not value.startswith(("http://", "https://")):
            raise ValueError("similar project URL must be an absolute http(s) link")
        return value[:2000]


class AdvancedUpgrade(BaseModel):
    upgrade_title: str = Field(..., description="Concrete next-stage upgrade title")
    inspired_by: str = Field(..., description="Real startup, paper, or framework")
    reference_url: str = Field(..., description="Real, openable startup/research/framework URL")
    architectural_impact: str = Field(default="", description="Concrete technical benefit")
    difficulty: str = Field(default="2-Week Milestone")

    @field_validator("upgrade_title", "inspired_by", mode="before")
    @classmethod
    def cap_title(cls, value: Any) -> str:
        return str(value or "")[:180]

    @field_validator("architectural_impact", mode="before")
    @classmethod
    def cap_impact(cls, value: Any) -> str:
        return str(value or "")[:800]

    @field_validator("difficulty", mode="before")
    @classmethod
    def cap_difficulty(cls, value: Any) -> str:
        text = str(value or "").strip()
        if text not in {"Weekend Sprint", "2-Week Milestone"}:
            text = "2-Week Milestone"
        return text[:40]

    @field_validator("reference_url")
    @classmethod
    def validate_reference_url(cls, value: str) -> str:
        value = (value or "").strip()
        if not value.startswith(("http://", "https://")):
            raise ValueError("upgrade reference URL must be an absolute http(s) link")
        return value[:2000]


def _cap_three(value: Any) -> List[Any]:
    return list(value or [])[:3]


class EcosystemBenchmark(BaseModel):
    similar_projects: List[SimilarProject] = Field(default_factory=list)
    advanced_upgrades: List[AdvancedUpgrade] = Field(default_factory=list)
    selected_upgrades: List[AdvancedUpgrade] = Field(default_factory=list)
    generated_at: Optional[datetime] = None
    query_basis: Optional[str] = Field(default=None)

    @field_validator("similar_projects", "advanced_upgrades", "selected_upgrades", mode="before")
    @classmethod
    def cap_lists(cls, value: Any) -> List[Any]:
        return _cap_three(value)

    @field_validator("query_basis", mode="before")
    @classmethod
    def cap_query_basis(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        return str(value)[:300]


class RoadmapUpdateRequest(BaseModel):
    selected_upgrades: List[AdvancedUpgrade] = Field(default_factory=list)

    @field_validator("selected_upgrades", mode="before")
    @classmethod
    def cap_selected(cls, value: Any) -> List[Any]:
        return _cap_three(value)


class DossierIngestRequest(BaseModel):
    input_type: Literal["github", "idea", "pdf_text", "pdf", "figma", "url"] = Field(
        ...,
        description="'github' | 'idea' | 'pdf_text' | 'pdf' | 'figma' | 'url'",
    )
    raw_content: str = Field(
        ...,
        min_length=5,
        max_length=100_000,
        description="URL or raw text content of the project",
    )
    domain_persona: str = Field(default="tech_builder", description="Domain persona key")

    @field_validator("raw_content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 5:
            raise ValueError("raw_content must contain at least 5 non-whitespace characters.")
        return value

    @field_validator("domain_persona")
    @classmethod
    def validate_persona(cls, value: str) -> str:
        value = value.strip().lower()
        if not _PERSONA_PATTERN.fullmatch(value):
            raise ValueError("domain_persona must be a lowercase identifier such as 'tech_builder'.")
        if value not in settings.KNOWN_PERSONAS:
            raise ValueError(
                f"Unknown domain_persona '{value}'. Expected one of: "
                + ", ".join(settings.KNOWN_PERSONAS)
            )
        return value


class DossierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None
    slug: str
    title: str
    tagline: str
    domain_persona: str
    domain: Optional[str] = None
    stage: str = "Prototype"
    problem_statement: str
    solution_breakdown: Dict[str, Any]
    solution_architecture: Optional[str] = None
    tech_stack: List[str]
    key_metrics: List[KeyMetric]
    whitespace_analysis: Optional[WhitespaceAnalysis] = None
    trend_radar_cache: Optional[Dict[str, Any]] = None
    benchmark_analysis: Optional[EcosystemBenchmark] = None
    missing_roles: List[MissingRole] = Field(default_factory=list)
    external_links: Dict[str, Any] = Field(default_factory=dict)
    verified_links: Dict[str, Any] = Field(default_factory=dict)
    verified_status: bool = False
    boosted: bool = False
    is_boost_active: bool = False
    boosted_until: Optional[datetime] = None
    boost_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class DossierVerifyResponse(BaseModel):
    dossier_id: UUID
    verified_status: bool
    checked_urls: Dict[str, int]
