import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base

class ProjectDossier(Base):
    __tablename__ = "project_dossiers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    guest_session_id = Column(String(100), nullable=True, index=True)
    slug = Column(String(150), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    tagline = Column(String(300), nullable=False)
    domain_persona = Column(String(50), nullable=False, default="tech_builder", index=True)
    stage = Column(String(40), nullable=False, default="Prototype", index=True)
    problem_statement = Column(Text, nullable=False)
    solution_breakdown = Column(JSONB, nullable=False)
    tech_stack = Column(JSONB, nullable=False, default=list)
    key_metrics = Column(JSONB, nullable=False, default=list)
    whitespace_analysis = Column(JSONB, nullable=True)
    trend_radar_cache = Column(JSONB, nullable=True)
    benchmark_analysis = Column(JSONB, nullable=True)
    missing_roles = Column(JSONB, nullable=False, default=list)
    external_links = Column(JSONB, nullable=False, default=dict)
    verified_status = Column(Boolean, default=False)
    boosted = Column(Boolean, default=False)
    boosted_until = Column(DateTime(timezone=True), nullable=True, index=True)
    embedding = Column(Vector(768), nullable=True)
    missing_roles_embedding = Column(Vector(768), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="dossiers")
    pr_assets = relationship("PRAsset", back_populates="dossier", cascade="all, delete-orphan")
    reach_events = relationship("PRReachEvent", back_populates="dossier", cascade="all, delete-orphan")

    # ------------------------------------------------------------------
    # Product-spec aliases. The database keeps the original column names
    # (which the existing frontend depends on) while serializers can expose
    # the canonical names from the supplied schema.
    # ------------------------------------------------------------------
    @property
    def owner_id(self):
        return self.user_id

    @property
    def domain(self) -> str:
        return self.domain_persona

    @property
    def solution_architecture(self) -> str:
        breakdown = self.solution_breakdown or {}
        if isinstance(breakdown, dict):
            return str(breakdown.get("architecture") or breakdown.get("summary") or "")
        return str(breakdown)

    @property
    def verified_links(self):
        return self.external_links or {}

    @property
    def project_embedding(self):
        return self.embedding

    @property
    def boost_expires_at(self):
        return self.boosted_until

    @property
    def is_boost_active(self) -> bool:
        if not self.boosted or not self.boosted_until:
            return False
        value = self.boosted_until
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value > datetime.now(timezone.utc)

