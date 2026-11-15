from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

class ContactMatchRequest(BaseModel):
    hashes: List[str] = Field(..., description="Array of 64-char lowercase SHA-256 email hashes")

class MatchedContact(BaseModel):
    user_id: UUID
    full_name: str
    avatar_url: Optional[str] = None
    active_dossiers_count: int = 0
    is_connected: bool = False

class ContactMatchResponse(BaseModel):
    matched_contacts: List[MatchedContact]

class InviteSendRequest(BaseModel):
    dossier_id: UUID
    recipient_email_hash: str = Field(..., description="64-character SHA-256 hash")
    role_context: Optional[str] = Field(default="Contributor / Peer Reviewer")

class InviteSendResponse(BaseModel):
    status: str
    invite_token: str
    whatsapp_url: str
    daily_invites_remaining: int

