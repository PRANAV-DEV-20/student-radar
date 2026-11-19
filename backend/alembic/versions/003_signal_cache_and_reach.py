"""signal_cache_and_reach

Adds:
- signal_cache: persisted market-intelligence snapshots with TTL
- pr_reach_events: anonymous dossier/PR-asset engagement events

Revision ID: 003_signal_cache_and_reach
Revises: 002_product_spec_alignment
Create Date: 2026-11-19 02:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_signal_cache_and_reach"
down_revision: Union[str, None] = "002_product_spec_alignment"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "signal_cache",
        sa.Column("cache_key", sa.String(length=255), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=True),
        sa.Column("is_live", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now() + interval '3 hours'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("cache_key"),
    )
    op.create_index("ix_signal_cache_expires_at", "signal_cache", ["expires_at"])

    op.create_table(
        "pr_reach_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dossier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pr_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column(
            "event_metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["dossier_id"], ["project_dossiers.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["pr_asset_id"], ["pr_assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pr_reach_events_dossier_id", "pr_reach_events", ["dossier_id"])
    op.create_index("ix_pr_reach_events_pr_asset_id", "pr_reach_events", ["pr_asset_id"])
    op.create_index("ix_pr_reach_events_event_type", "pr_reach_events", ["event_type"])
    op.create_index("ix_pr_reach_events_created_at", "pr_reach_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_pr_reach_events_created_at", table_name="pr_reach_events")
    op.drop_index("ix_pr_reach_events_event_type", table_name="pr_reach_events")
    op.drop_index("ix_pr_reach_events_pr_asset_id", table_name="pr_reach_events")
    op.drop_index("ix_pr_reach_events_dossier_id", table_name="pr_reach_events")
    op.drop_table("pr_reach_events")
    op.drop_index("ix_signal_cache_expires_at", table_name="signal_cache")
    op.drop_table("signal_cache")
