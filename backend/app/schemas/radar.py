from typing import Any, Dict, List, Literal, Optional
from datetime import date, datetime
from uuid import UUID
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings
from app.schemas.signals import MarketSignal

RadarIntent = Literal[
    "hackathons", "news", "builders", "events", "grants", "trends", "opportunities"
]

class OpportunityBase(BaseModel):
    id: UUID
    title: str
    category: str
    canonical_source_url: str
    host_organization: Optional[str] = None
    organizer: Optional[str] = None
    deadline: datetime
    deadline_at: Optional[datetime] = None
    city: Optional[str] = None
    event_date: Optional[date] = None
    description: str
    tags: List[str] = Field(default_factory=list)
    domain_personas: List[str] = Field(default_factory=list)
    persona_tags: List[str] = Field(default_factory=list)
    location_type: str = "virtual"
    mode: Optional[str] = None
    reward_pool: Optional[str] = None
    decision_metadata: Dict[str, Any] = Field(default_factory=dict)

class UrgentDeadline(BaseModel):
    id: UUID
    title: str
    category: str
    deadline: datetime
    hours_remaining: int
    reward_pool: Optional[str] = None

class NetworkingPlan(BaseModel):
    target_stakeholders: List[str] = Field(default_factory=list)
    pitch_angle: str = ""
    icebreaker_message: str = ""
    conversation_starters: List[str] = Field(default_factory=list)
    followup_draft: str = ""

class StrongestPick(OpportunityBase):
    match_score: float = Field(..., ge=0.0, le=1.0)
    why_you_match: str
    networking_plan: NetworkingPlan

class RadarBriefingResponse(BaseModel):
    briefing_date: str
    briefing_type: str = "daily"
    persona: str
    urgent_deadlines: List[UrgentDeadline] = Field(default_factory=list)
    strongest_pick: Optional[StrongestPick] = None
    hackathons: List[OpportunityBase] = Field(default_factory=list)
    general_events: List[OpportunityBase] = Field(default_factory=list)
    all_opportunities: List[OpportunityBase] = Field(default_factory=list)


class ReprofileRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    persona_id: str = Field(
        ...,
        max_length=50,
        validation_alias=AliasChoices("persona_id", "persona", "active_persona_id"),
        description="Target PersonaConfig identifier",
    )

    @field_validator("persona_id")
    @classmethod
    def validate_persona(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in settings.KNOWN_PERSONAS:
            raise ValueError(
                f"Unknown persona '{value}'. Expected one of: "
                + ", ".join(settings.KNOWN_PERSONAS)
            )
        return value


class ReprofileResponse(BaseModel):
    status: str = "updated"
    persona: str
    active_persona_id: str
    briefing: RadarBriefingResponse


class ScanLiveRequest(BaseModel):
    raw_idea: Optional[str] = Field(default=None, description="Free-form idea text. No upper length limit.")
    persona: str = settings.DEFAULT_PERSONA
    dossier_id: Optional[UUID] = None
    dossier_slug: Optional[str] = None
    intents: List[RadarIntent] = Field(
        default_factory=lambda: ["hackathons", "news", "builders", "events", "grants"]
    )
    language: str = settings.RADAR_SCAN_LANGUAGE
    max_age_hours: int = Field(default=0, ge=0, le=720)

    @field_validator("persona")
    @classmethod
    def validate_persona(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in settings.KNOWN_PERSONAS:
            raise ValueError(f"Unknown persona '{value}'.")
        return value

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        value = value.strip().lower()
        if not value:
            return settings.RADAR_SCAN_LANGUAGE
        return value[:20]

    @field_validator("intents")
    @classmethod
    def limit_intents(cls, value: List[RadarIntent]) -> List[RadarIntent]:
        unique = list(dict.fromkeys(value))
        if not unique:
            return ["hackathons", "news", "builders", "events", "grants"]
        return unique[: settings.RADAR_ON_DEMAND_MAX_INTENTS]


class RadarQueryPlan(BaseModel):
    intent: str
    query: str
    raw_results: int = 0
    actionable_after_gatekeeper: int = 0
    accepted: int = 0
    note: Optional[str] = None


class RadarSourceStatus(BaseModel):
    source: str
    label: str
    status: str
    raw_count: int = 0
    accepted_count: int = 0
    is_official: bool = False
    note: Optional[str] = None


class ScanLiveStats(BaseModel):
    raw_results: int = 0
    actionable_after_gatekeeper: int = 0
    accepted: int = 0
    rejected: int = 0
    opportunities_inserted: int = 0
    opportunities_merged: int = 0
    relevance_filtered: int = 0
    llm_verified: int = 0
    duration_ms: int = 0


class ScanLiveResponse(BaseModel):
    status: str
    persona: str
    language: str
    max_age_hours: int
    concept_profile: Dict[str, Any] = Field(default_factory=dict)
    radar_queries: Dict[str, str] = Field(default_factory=dict)
    queries: List[RadarQueryPlan] = Field(default_factory=list)
    sources: List[RadarSourceStatus] = Field(default_factory=list)
    stats: ScanLiveStats
    briefing: RadarBriefingResponse
    signals: List[MarketSignal] = Field(default_factory=list)

