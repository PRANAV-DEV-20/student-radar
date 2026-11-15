from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class OpportunityBase(BaseModel):
    id: UUID
    title: str
    category: str
    canonical_source_url: str
    host_organization: Optional[str] = None
    deadline: datetime
    description: str
    tags: List[str] = Field(default_factory=list)
    domain_personas: List[str] = Field(default_factory=list)
    location_type: str = "virtual"
    reward_pool: Optional[str] = None

class UrgentDeadline(BaseModel):
    id: UUID
    title: str
    category: str
    deadline: datetime
    hours_remaining: int
    reward_pool: Optional[str] = None

class NetworkingPlan(BaseModel):
    target_stakeholders: List[str] = Field(default_factory=list)
    pitch_angle: str
    icebreaker_message: str

class StrongestPick(OpportunityBase):
    match_score: float = Field(..., ge=0.0, le=1.0)
    why_you_match: str
    networking_plan: NetworkingPlan

class RadarBriefingResponse(BaseModel):
    briefing_date: str
    persona: str
    urgent_deadlines: List[UrgentDeadline]
    strongest_pick: Optional[StrongestPick] = None
    all_opportunities: List[OpportunityBase]

