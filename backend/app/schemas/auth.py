from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.config import settings


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    full_name: Optional[str] = None
    email: str
    credits_balance: int


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    oauth_provider: Optional[str] = None
    campus_or_org: Optional[str] = None
    city: Optional[str] = None
    active_persona_id: str = "tech_builder"
    verified_skills: list[str] = Field(default_factory=list)
    credits_balance: int


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(..., min_length=1, description="Google ID token (or a simulated token in development)")
    guest_session_id: Optional[str] = Field(default=None, max_length=100)
    referral_token: Optional[str] = Field(default=None, max_length=64)


class ClaimGuestRequest(BaseModel):
    guest_session_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="The temporary guest session identifier",
    )


class ClaimGuestResponse(BaseModel):
    status: str
    claimed_dossiers_count: int
    user_id: UUID
    credits_balance: int


class UserRegisterRequest(BaseModel):
    email: EmailStr
    # bcrypt has a hard 72-byte limit; rejecting longer values here yields a
    # clean 422 instead of a server error during hashing.
    password: str = Field(..., min_length=6, max_length=72)
    full_name: str = Field(..., min_length=1, max_length=120)
    campus_or_org: Optional[str] = Field(default=None, max_length=160)
    city: Optional[str] = Field(default=None, max_length=100)
    active_persona_id: str = Field(default="tech_builder", max_length=50)
    verified_skills: list[str] = Field(default_factory=list, max_length=40)
    guest_session_id: Optional[str] = Field(default=None, max_length=100)
    referral_token: Optional[str] = Field(default=None, max_length=64)

    @field_validator("email", "full_name")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("campus_or_org", "city")
    @classmethod
    def strip_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("full_name")
    @classmethod
    def require_name(cls, value: str) -> str:
        if not value:
            raise ValueError("Full name cannot be blank.")
        return value

    @field_validator("active_persona_id")
    @classmethod
    def validate_persona(cls, value: str) -> str:
        value = (value or "").strip().lower()
        if not value or not value.replace("_", "").isalnum():
            raise ValueError("active_persona_id must be an identifier such as 'tech_builder'.")
        if value not in settings.KNOWN_PERSONAS:
            raise ValueError(
                f"Unknown active_persona_id '{value}'. Expected one of: "
                + ", ".join(settings.KNOWN_PERSONAS)
            )
        return value

    @field_validator("verified_skills")
    @classmethod
    def normalize_skills(cls, values: list[str]) -> list[str]:
        cleaned = [str(value).strip()[:80] for value in values if str(value).strip()]
        return list(dict.fromkeys(cleaned))[:40]


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    campus_or_org: Optional[str] = Field(default=None, max_length=160)
    city: Optional[str] = Field(default=None, max_length=100)
    active_persona_id: Optional[str] = Field(default=None, max_length=50)
    verified_skills: Optional[list[str]] = Field(default=None, max_length=40)

    @field_validator("full_name", "campus_or_org", "city", "active_persona_id")
    @classmethod
    def strip_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("active_persona_id")
    @classmethod
    def validate_persona(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.lower()
        if not value.replace("_", "").isalnum():
            raise ValueError("active_persona_id must be an identifier such as 'tech_builder'.")
        if value not in settings.KNOWN_PERSONAS:
            raise ValueError(
                f"Unknown active_persona_id '{value}'. Expected one of: "
                + ", ".join(settings.KNOWN_PERSONAS)
            )
        return value

    @field_validator("verified_skills")
    @classmethod
    def normalize_skills(cls, values: Optional[list[str]]) -> Optional[list[str]]:
        if values is None:
            return None
        cleaned = [str(value).strip()[:80] for value in values if str(value).strip()]
        return list(dict.fromkeys(cleaned))[:40]


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)
    guest_session_id: Optional[str] = Field(default=None, max_length=100)

    @field_validator("email")
    @classmethod
    def strip_email(cls, value: str) -> str:
        return value.strip()
