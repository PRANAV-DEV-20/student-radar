from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class PRGenerateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    dossier_id: UUID
    playbook_type: Literal[
        "linkedin",
        "instagram_reel",
        "instagram_carousel",
        "x_thread",
        "show_hn",
        "reel_script",
        "cold_pitch",
        "policy_brief",
        "plain_explainer",
    ] = Field(
        default="linkedin",
        validation_alias=AliasChoices("playbook_type", "platform", "platform_type"),
        description="Domain-agnostic content format pack key.",
    )
    tone: Literal[
        "academic", "high_octane", "executive", "founder", "storyteller", "humble_beginner"
    ] = Field(default="high_octane", description="Voice used for the generated copy.")
    target_audience: Optional[str] = Field(
        default="Peer builders, technical founders, and investors", max_length=300
    )
    target_opportunity_id: Optional[UUID] = Field(
        default=None,
        description="When set, the pitch is tailored to this radar opportunity.",
    )
    target_opportunity_context: Optional[str] = Field(
        default=None,
        max_length=4000,
        description="Optional free-text brief for application-specific tailoring.",
    )


class PRGenerateResponse(BaseModel):
    asset_id: UUID
    asset_type: str
    platform: Optional[str] = None
    headline: str
    body_markdown: str
    hooks: List[str] = Field(default_factory=list)
    suggested_tags: List[str] = Field(default_factory=list)
    structured_payload: Dict[str, Any] = Field(default_factory=dict)
    og_image_url: Optional[str] = None
    launch_card_url: Optional[str] = None


class PRBoostResponse(BaseModel):
    status: str
    dossier_id: Optional[UUID] = None
    credits_deducted: int
    remaining_balance: int
    boost_expires_at: datetime


class PRReachEventRequest(BaseModel):
    event_type: Literal["view", "copy", "share", "dossier_view"]
    guest_session_id: Optional[str] = Field(default=None, max_length=100)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PRReachAnalyticsResponse(BaseModel):
    total: int
    by_event_type: Dict[str, int] = Field(default_factory=dict)
    dossier_views: int = 0
    asset_views: int = 0
    latest_event_at: Optional[datetime] = None
