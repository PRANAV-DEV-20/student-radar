import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base

class PRAsset(Base):
    __tablename__ = "pr_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dossier_id = Column(UUID(as_uuid=True), ForeignKey("project_dossiers.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_type = Column(String(50), nullable=False) # 'linkedin', 'instagram_reel', 'cold_pitch', 'launch_card'
    content_json = Column(JSONB, nullable=False)
    og_image_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    dossier = relationship("ProjectDossier", back_populates="pr_assets")

