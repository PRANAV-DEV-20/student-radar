import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class PRReachEvent(Base):
    """Anonymous engagement event for a dossier or generated PR asset."""

    __tablename__ = "pr_reach_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dossier_id = Column(
        UUID(as_uuid=True),
        ForeignKey("project_dossiers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pr_asset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pr_assets.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    event_type = Column(String(30), nullable=False, index=True)
    event_metadata = Column("event_metadata", JSONB, nullable=False, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    dossier = relationship("ProjectDossier", back_populates="reach_events")
    pr_asset = relationship("PRAsset", back_populates="reach_events")
