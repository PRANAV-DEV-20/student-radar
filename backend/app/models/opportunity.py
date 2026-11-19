import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Date, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from app.core.database import Base

class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(250), nullable=False)
    category = Column(String(50), nullable=False) # 'hackathon', 'build_sprint', 'general_event', 'grant', 'fellowship', 'conference'
    canonical_source_url = Column(Text, unique=True, nullable=False, index=True)
    host_organization = Column(String(150), nullable=True)
    deadline = Column(DateTime(timezone=True), nullable=False, index=True)
    city = Column(String(100), nullable=True, index=True)
    event_date = Column(Date, nullable=True, index=True)
    description = Column(Text, nullable=False)
    tags = Column(JSONB, nullable=False, default=list)
    domain_personas = Column(JSONB, nullable=False, default=list) # e.g. ["tech_builder"]
    location_type = Column(String(50), default="virtual") # 'virtual', 'in_person', 'hybrid'
    reward_pool = Column(String(100), nullable=True)
    decision_metadata = Column(JSONB, nullable=False, default=dict)
    embedding = Column(Vector(768), nullable=True)
    sha256_hash = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Canonical product-schema aliases (existing API fields stay intact).
    @property
    def fingerprint(self) -> str:
        return self.sha256_hash

    @property
    def persona_tags(self):
        return self.domain_personas or []

    @property
    def organizer(self):
        return self.host_organization

    @property
    def mode(self):
        return self.location_type

    @property
    def deadline_at(self):
        return self.deadline

    @property
    def summary_embedding(self):
        return self.embedding

