import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.core.config import settings
from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("credits_balance >= 0", name="ck_users_credits_non_negative"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)
    full_name = Column(String(120), nullable=True)
    avatar_url = Column(Text, nullable=True)
    oauth_provider = Column(String(50), default="google")
    oauth_id = Column(String(255), nullable=True)
    campus_or_org = Column(String(160), nullable=True)
    city = Column(String(100), nullable=False, default=settings.DEFAULT_CITY)
    active_persona_id = Column(
        String(50), nullable=False, default=settings.DEFAULT_PERSONA, index=True
    )
    # JSONB keeps this portable across the asyncpg / SQLAlchemy stack while
    # behaving like the TEXT[] column described in the product schema.
    verified_skills = Column(JSONB, nullable=False, default=list)
    skills_embedding = Column(Vector(768), nullable=True)
    credits_balance = Column(Integer, default=settings.SIGNUP_CREDITS, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Dossiers are public proof-of-work artifacts: deleting an account must
    # leave them online with ``user_id = NULL`` (matching the FK's SET NULL).
    dossiers = relationship("ProjectDossier", back_populates="user", passive_deletes=True)
    briefings = relationship("UserBriefing", back_populates="user", cascade="all, delete-orphan")
    credit_transactions = relationship("CreditTransaction", back_populates="user", cascade="all, delete-orphan")
