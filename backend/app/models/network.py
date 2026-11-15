import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class ReferralInvite(Base):
    __tablename__ = "referral_invites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_email_hash = Column(String(64), nullable=False, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    status = Column(String(30), default="pending", nullable=False) # 'pending', 'claimed', 'expired'
    claimed_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    sender = relationship("User", foreign_keys=[sender_user_id])
    claimed_user = relationship("User", foreign_keys=[claimed_user_id])

class SuppressedEmail(Base):
    __tablename__ = "suppressed_emails"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_hash = Column(String(64), unique=True, nullable=False, index=True)
    reason = Column(String(100), default="user_opt_out")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

