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
    reach_events = relationship("PRReachEvent", back_populates="pr_asset", cascade="all, delete-orphan")

    # Canonical product-schema aliases.
    @property
    def platform(self) -> str:
        return self.asset_type

    @property
    def structured_payload(self):
        return self.content_json

    @property
    def launch_card_url(self):
        return self.og_image_url

