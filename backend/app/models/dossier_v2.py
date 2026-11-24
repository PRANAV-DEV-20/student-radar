"""ORM models for the Dossier v2 research pipeline."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def _now():
    return datetime.now(timezone.utc)


class DossierRun(Base):
    __tablename__ = "dossier_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("project_dossiers.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    guest_session_id = Column(String(100), nullable=True, index=True)
    status = Column(String(30), nullable=False, default="running")
    mode = Column(String(10), nullable=False, default="deep")
    input_type = Column(String(20), nullable=False)
    raw_content = Column(Text, nullable=False)
    domain_persona = Column(String(50), nullable=False, default="tech_builder")
    profile = Column(JSONB, nullable=False, default=dict)
    project_dna = Column(JSONB, nullable=True)
    plan = Column(JSONB, nullable=True)
    coverage = Column(JSONB, nullable=True)
    progress = Column(JSONB, nullable=False, default=dict)
    tasks = Column(JSONB, nullable=False, default=list)
    error = Column(Text, nullable=True)
    cost_usd = Column(Numeric(10, 4), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    evidence = relationship("Evidence", back_populates="run", cascade="all, delete-orphan", passive_deletes=True)
    ai_runs = relationship("AIRun", back_populates="run", cascade="all, delete-orphan", passive_deletes=True)
    sections = relationship("DossierSection", back_populates="run", cascade="all, delete-orphan", passive_deletes=True)
    reviews = relationship("SectionReview", back_populates="run", cascade="all, delete-orphan", passive_deletes=True)
    sources = relationship("DossierSource", back_populates="run", cascade="all, delete-orphan", passive_deletes=True)
    versions = relationship("DossierVersion", back_populates="run", cascade="all, delete-orphan", passive_deletes=True)


class AIRun(Base):
    """One real LLM call, used for the per-run ai_runs audit trail."""

    __tablename__ = "ai_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("dossier_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    role = Column(String(30), nullable=False)
    model = Column(String(80), nullable=False)
    success = Column(Boolean, nullable=False, default=True)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    latency_ms = Column(Integer, nullable=False, default=0)
    attempts = Column(Integer, nullable=False, default=1)
    fallback_used = Column(Boolean, nullable=False, default=False)
    cached = Column(Boolean, nullable=False, default=False)
    cost_usd = Column(Numeric(12, 6), nullable=False, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    run = relationship("DossierRun", back_populates="ai_runs")


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("dossier_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    ref = Column(String(20), nullable=False)
    question_id = Column(String(30), nullable=True, index=True)
    url = Column(Text, nullable=False)
    title = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)
    source_quality = Column(String(30), nullable=True)
    passage = Column(Text, nullable=False)
    relevance = Column(SmallInteger, nullable=True)
    canonical_key = Column(String(500), nullable=True)
    retrieved_at = Column(DateTime(timezone=True), nullable=False, default=_now)

    run = relationship("DossierRun", back_populates="evidence")


class DossierSource(Base):
    __tablename__ = "dossier_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("dossier_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    ref = Column(String(20), nullable=False)
    url = Column(Text, nullable=False)
    title = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)
    source_quality = Column(String(30), nullable=True)
    retrieved_at = Column(DateTime(timezone=True), default=_now)

    run = relationship("DossierRun", back_populates="sources")


class SectionReview(Base):
    __tablename__ = "section_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("dossier_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    section = Column(String(60), nullable=False)
    attempt = Column(Integer, nullable=False)
    passed = Column(Boolean, nullable=False)
    failures = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)

    run = relationship("DossierRun", back_populates="reviews")


class DossierSection(Base):
    __tablename__ = "dossier_sections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("dossier_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    section = Column(String(60), nullable=False)
    content = Column(JSONB, nullable=False)
    confidence = Column(String(10), nullable=True)
    coverage = Column(String(10), nullable=True)
    locked = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime(timezone=True), default=_now)

    run = relationship("DossierRun", back_populates="sections")


class DossierVersion(Base):
    __tablename__ = "dossier_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("dossier_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    snapshot = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)

    run = relationship("DossierRun", back_populates="versions")
