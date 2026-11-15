from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, model_validator

class ReviewRubric(BaseModel):
    strength: str = Field(..., description="Key technical or product strength")
    bottleneck: str = Field(..., description="Observed vulnerability, bottleneck, or scaling limitation")
    suggestion: str = Field(..., description="Concrete, actionable improvement or architectural alternative")

class PeerReviewRequest(BaseModel):
    dossier_id: UUID
    rubric: ReviewRubric

    @model_validator(mode="after")
    def validate_length(self):
        total_len = len(self.rubric.strength.strip()) + len(self.rubric.bottleneck.strip()) + len(self.rubric.suggestion.strip())
        if total_len < 80:
            raise ValueError(f"Peer review rubric must contain at least 80 characters in total (current: {total_len}).")
        return self

class PeerReviewResponse(BaseModel):
    status: str
    credits_awarded: int
    new_balance: int

class CreditBalanceResponse(BaseModel):
    user_id: UUID
    credits_balance: int

