"""ecosystem_benchmark

Adds a single JSONB column to project_dossiers for the two-tier
Ecosystem Benchmark & Evolution Roadmap: peer/lookalike projects,
production-grade upgrades, and the student's selected roadmap items.

Revision ID: 004_ecosystem_benchmark
Revises: 003_signal_cache_and_reach
Create Date: 2026-11-19 15:10:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_ecosystem_benchmark"
down_revision: Union[str, None] = "003_signal_cache_and_reach"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "project_dossiers",
        sa.Column("benchmark_analysis", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("project_dossiers", "benchmark_analysis")
