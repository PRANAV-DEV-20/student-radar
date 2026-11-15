import uuid
from datetime import datetime, timezone, date
from sqlalchemy import Column, String, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base

class UserBriefing(Base):
    __tablename__ = "user_briefings"
    __table_args__ = (
        UniqueConstraint("user_id", "briefing_date", name="unique_user_briefing_per_day"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    briefing_date = Column(Date, default=lambda: datetime.now(timezone.utc).date(), nullable=False)
    opportunity_ids = Column(JSONB, nullable=False, default=list)
    strongest_pick_id = Column(UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True)
    networking_plan_json = Column(JSONB, nullable=True)
    persona_mode = Column(String(50), nullable=False, default="tech_builder")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="briefings")
    strongest_pick = relationship("Opportunity")

