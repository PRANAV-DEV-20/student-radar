"""Schemas for cross-platform market and competitor intelligence."""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

SignalSource = Literal[
    "founderdb",
    "ideabrowser",
    "tumrr",
    "google_trends",
    "x",
    "reddit",
    "threads",
    "news",
    "hackernews",
    "indiehackers",
    "builder",
]

SignalType = Literal["competitor", "discussion", "trend", "builder", "news"]


class MarketSignal(BaseModel):
    """One externally sourced signal about a dossier's problem space."""

    id: str
    source: SignalSource
    signal_type: SignalType
    title: str
    summary: str
    url: str
    published_at: Optional[datetime] = None
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    keywords: List[str] = Field(default_factory=list)
    is_live: bool = False
    radar_intent: Optional[str] = None


class BuilderMatch(BaseModel):
    """An adjacent builder/project discovered through a live signal."""

    id: str
    name: str
    platform: SignalSource
    profile_url: str
    overlap_tags: List[str] = Field(default_factory=list)
    outreach_hook: str
    is_live: bool = True


class SourceCoverage(BaseModel):
    """Whether a source produced grounded results or only exploration links."""

    source: SignalSource
    live: bool
    signal_count: int
    note: Optional[str] = None


class MarketIntelligenceResponse(BaseModel):
    generated_at: datetime
    title: Optional[str] = None
    domain_persona: str
    keywords: List[str] = Field(default_factory=list)
    trend_direction: Literal["rising", "steady", "emerging", "unknown"] = "unknown"
    trend_basis: str
    summary: str
    signals: List[MarketSignal] = Field(default_factory=list)
    similar_builders: List[BuilderMatch] = Field(default_factory=list)
    coverage: List[SourceCoverage] = Field(default_factory=list)
