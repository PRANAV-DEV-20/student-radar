from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


class ReviewRubric(BaseModel):
    strength: str = Field(..., min_length=1, max_length=2000, description="Key technical or product strength")
    bottleneck: str = Field(
        ..., min_length=1, max_length=2000, description="Observed vulnerability, bottleneck, or scaling limitation"
    )
    suggestion: str = Field(
        ..., min_length=1, max_length=2000, description="Concrete, actionable improvement or architectural alternative"
    )

    @field_validator("strength", "bottleneck", "suggestion")
    @classmethod
    def strip_field(cls, value: str) -> str:
        return value.strip()


class PeerReviewRequest(BaseModel):
    dossier_id: UUID
    rubric: ReviewRubric

    @model_validator(mode="after")
    def validate_length(self):
        total_len = (
            len(self.rubric.strength)
            + len(self.rubric.bottleneck)
            + len(self.rubric.suggestion)
        )
        if total_len < 80:
            raise ValueError(
                f"Peer review rubric must contain at least 80 characters in total (current: {total_len})."
            )
        return self


class PeerReviewResponse(BaseModel):
    status: str
    dossier_id: Optional[UUID] = None
    credits_awarded: int
    new_balance: int


class CreditBalanceResponse(BaseModel):
    user_id: UUID
    credits_balance: int


class CreditTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    dossier_id: Optional[UUID] = None
    delta: int = Field(validation_alias=AliasChoices("delta", "amount"))
    reason: str
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        # ``metadata`` is a reserved SQLAlchemy declarative attribute, so the
        # ORM column ``metadata_json`` must be probed first.
        validation_alias=AliasChoices("metadata_json", "metadata"),
    )
    created_at: datetime


class CreditHistoryResponse(BaseModel):
    user_id: UUID
    transactions: List[CreditTransactionResponse] = Field(default_factory=list)
    credits_balance: int
