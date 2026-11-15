from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class PRGenerateRequest(BaseModel):
    dossier_id: UUID
    playbook_type: str = Field(default="linkedin", description="'linkedin' | 'instagram_reel' | 'cold_pitch'")
    tone: str = Field(default="high_octane", description="'academic' | 'high_octane' | 'executive'")
    target_audience: Optional[str] = Field(default="Peer builders, technical founders, and investors")

class PRGenerateResponse(BaseModel):
    asset_type: str
    headline: str
    body_markdown: str
    hooks: List[str] = Field(default_factory=list)
    suggested_tags: List[str] = Field(default_factory=list)
    og_image_url: Optional[str] = None

class PRBoostResponse(BaseModel):
    status: str
    credits_deducted: int
    remaining_balance: int
    boost_expires_at: datetime

