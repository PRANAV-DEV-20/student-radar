import logging
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base

logger = logging.getLogger(__name__)


class SignalCache(Base):
    """A persisted snapshot of external market intelligence.

    Search-provider calls are relatively slow and rate-limited. Snapshots are
    refreshed by Celery beat and served from this table until they expire.
    """

    __tablename__ = "signal_cache"

    cache_key = Column(String(255), primary_key=True)
    payload = Column(JSONB, nullable=False)
    provider = Column(String(32), nullable=True)
    is_live = Column(Boolean, nullable=False, default=False)
    generated_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
