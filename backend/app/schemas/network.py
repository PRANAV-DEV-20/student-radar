from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.core.security import is_valid_sha256


class ContactMatchRequest(BaseModel):
    hashes: List[str] = Field(
        ...,
        min_length=0,
        max_length=settings.MAX_CONTACT_HASHES,
        description="Array of 64-char lowercase SHA-256 email hashes",
    )

    @field_validator("hashes")
    @classmethod
    def normalize_hashes(cls, values: List[str]) -> List[str]:
        normalized: List[str] = []
        for value in values:
            if not isinstance(value, str):
                continue
            value = value.strip().lower()
            # Silently ignore malformed entries rather than rejecting the whole
            # batch; clients may paste mixed contact lists.
            if is_valid_sha256(value):
                normalized.append(value)
        return list(dict.fromkeys(normalized))


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
    role_context: Optional[str] = Field(default="Contributor / Peer Reviewer", max_length=120)

    @field_validator("recipient_email_hash")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        value = value.strip().lower()
        if not is_valid_sha256(value):
            raise ValueError("recipient_email_hash must be a 64-character lowercase SHA-256 hex digest.")
        return value


class InviteSendResponse(BaseModel):
    status: str
    invite_token: str
    whatsapp_url: str
    daily_invites_remaining: int
