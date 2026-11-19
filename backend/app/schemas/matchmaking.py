from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CoBuilderMatch(BaseModel):
    user_id: UUID
    full_name: str
    avatar_url: Optional[str] = None
    campus_or_org: Optional[str] = None
    city: Optional[str] = None
    active_persona_id: str = "tech_builder"
    verified_skills: List[str] = Field(default_factory=list)
    matched_roles: List[str] = Field(default_factory=list)
    match_score: float = Field(..., ge=0.0, le=1.0)
    match_reason: str
    active_dossiers_count: int = 0
    is_connected: bool = False


class CoBuilderMatchResponse(BaseModel):
    dossier_id: UUID
    dossier_slug: str
    missing_roles: List[str] = Field(default_factory=list)
    matches: List[CoBuilderMatch] = Field(default_factory=list)
