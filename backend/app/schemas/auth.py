from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    full_name: Optional[str] = None
    email: str
    credits_balance: int

class GoogleAuthRequest(BaseModel):
    id_token: str
    guest_session_id: Optional[str] = None

class ClaimGuestRequest(BaseModel):
    guest_session_id: str = Field(..., description="The temporary guest session UUID")

class ClaimGuestResponse(BaseModel):
    status: str
    claimed_dossiers_count: int
    user_id: UUID
    credits_balance: int

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str
    guest_session_id: Optional[str] = None

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str
    guest_session_id: Optional[str] = None

