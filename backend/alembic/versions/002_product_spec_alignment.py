"""product_spec_alignment

Adds the extended product-schema fields:
- users: campus/org, city, active persona, verified skills + embedding
- project_dossiers: stage, trend radar cache, missing-roles embedding, boost expiry
- opportunities: city, event_date, decision metadata
- user_briefings: daily/weekly type, dossier link, ranked buckets, rationale
- credit_transactions: dossier link + one-review-per-dossier guarantee

Revision ID: 002_product_spec_alignment
Revises: 001_initial_schema
Create Date: 2026-11-15 23:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "002_product_spec_alignment"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    op.add_column("users", sa.Column("campus_or_org", sa.String(length=160), nullable=True))
    op.add_column(
        "users",
        sa.Column("city", sa.String(length=100), nullable=False, server_default="Pune"),
    )
    op.add_column(
        "users",
        sa.Column(
            "active_persona_id",
            sa.String(length=50),
            nullable=False,
            server_default="tech_builder",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "verified_skills",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column("users", sa.Column("skills_embedding", Vector(768), nullable=True))
    op.create_index("ix_users_active_persona_id", "users", ["active_persona_id"])
    op.execute(
        "ALTER TABLE users ALTER COLUMN credits_balance SET DEFAULT 30;"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_users_skills_embedding "
        "ON users USING hnsw (skills_embedding vector_cosine_ops);"
    )

    # ------------------------------------------------------------------
    # project_dossiers
    # ------------------------------------------------------------------
    op.add_column(
        "project_dossiers",
        sa.Column("stage", sa.String(length=40), nullable=False, server_default="Prototype"),
    )
    op.add_column(
        "project_dossiers",
        sa.Column("trend_radar_cache", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "project_dossiers",
        sa.Column("missing_roles_embedding", Vector(768), nullable=True),
    )
    op.add_column(
        "project_dossiers",
        sa.Column("boosted_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_project_dossiers_stage", "project_dossiers", ["stage"])
    op.create_index(
        "ix_project_dossiers_domain_persona",
        "project_dossiers",
        ["domain_persona"],
    )
    op.create_index("ix_project_dossiers_user_id", "project_dossiers", ["user_id"])
    op.create_index(
        "ix_project_dossiers_boosted_until", "project_dossiers", ["boosted_until"]
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_dossier_missing_roles_embedding "
        "ON project_dossiers USING hnsw (missing_roles_embedding vector_cosine_ops);"
    )

    # ------------------------------------------------------------------
    # opportunities
    # ------------------------------------------------------------------
    op.add_column("opportunities", sa.Column("city", sa.String(length=100), nullable=True))
    op.add_column("opportunities", sa.Column("event_date", sa.Date(), nullable=True))
    op.add_column(
        "opportunities",
        sa.Column(
            "decision_metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index("ix_opportunities_city", "opportunities", ["city"])
    op.create_index("ix_opportunities_event_date", "opportunities", ["event_date"])

    # ------------------------------------------------------------------
    # user_briefings
    # ------------------------------------------------------------------
    op.add_column(
        "user_briefings",
        sa.Column(
            "dossier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project_dossiers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "user_briefings",
        sa.Column("briefing_type", sa.String(length=20), nullable=False, server_default="daily"),
    )
    op.add_column(
        "user_briefings",
        sa.Column("strongest_pick_rationale", sa.Text(), nullable=True),
    )
    op.add_column(
        "user_briefings",
        sa.Column(
            "ranked_hackathons",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "user_briefings",
        sa.Column(
            "ranked_events",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.create_index("ix_user_briefings_dossier_id", "user_briefings", ["dossier_id"])
    op.create_index("ix_user_briefings_briefing_type", "user_briefings", ["briefing_type"])
    op.execute(
        "ALTER TABLE user_briefings "
        "DROP CONSTRAINT IF EXISTS unique_user_briefing_per_day;"
    )
    op.create_unique_constraint(
        "unique_user_briefing_per_type",
        "user_briefings",
        ["user_id", "briefing_date", "briefing_type"],
    )

    # ------------------------------------------------------------------
    # referral_invites
    # ------------------------------------------------------------------
    op.create_index(
        "ix_referral_invites_sender_user_id",
        "referral_invites",
        ["sender_user_id"],
    )
    op.add_column(
        "referral_invites",
        sa.Column(
            "dossier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project_dossiers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_referral_invites_dossier_id", "referral_invites", ["dossier_id"]
    )

    # ------------------------------------------------------------------
    # credit_transactions
    # ------------------------------------------------------------------
    op.create_index(
        "ix_credit_transactions_user_id", "credit_transactions", ["user_id"]
    )
    op.add_column(
        "credit_transactions",
        sa.Column(
            "dossier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project_dossiers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_credit_transactions_dossier_id", "credit_transactions", ["dossier_id"]
    )
    # Database-level guard against farming the same review repeatedly.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_credit_review_per_user_dossier "
        "ON credit_transactions (user_id, dossier_id) "
        "WHERE reason = 'review_peer' AND dossier_id IS NOT NULL;"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_credit_review_per_user_dossier;")
    op.drop_index("ix_credit_transactions_dossier_id", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_user_id", table_name="credit_transactions")
    op.drop_column("credit_transactions", "dossier_id")

    op.drop_index("ix_referral_invites_dossier_id", table_name="referral_invites")
    op.drop_index("ix_referral_invites_sender_user_id", table_name="referral_invites")
    op.drop_column("referral_invites", "dossier_id")

    op.execute(
        "ALTER TABLE user_briefings "
        "DROP CONSTRAINT IF EXISTS unique_user_briefing_per_type;"
    )
    op.create_unique_constraint(
        "unique_user_briefing_per_day",
        "user_briefings",
        ["user_id", "briefing_date"],
    )
    op.drop_index("ix_user_briefings_briefing_type", table_name="user_briefings")
    op.drop_index("ix_user_briefings_dossier_id", table_name="user_briefings")
    op.drop_column("user_briefings", "ranked_events")
    op.drop_column("user_briefings", "ranked_hackathons")
    op.drop_column("user_briefings", "strongest_pick_rationale")
    op.drop_column("user_briefings", "briefing_type")
    op.drop_column("user_briefings", "dossier_id")

    op.drop_index("ix_opportunities_event_date", table_name="opportunities")
    op.drop_index("ix_opportunities_city", table_name="opportunities")
    op.drop_column("opportunities", "decision_metadata")
    op.drop_column("opportunities", "event_date")
    op.drop_column("opportunities", "city")

    op.execute("DROP INDEX IF EXISTS idx_dossier_missing_roles_embedding;")
    op.drop_index("ix_project_dossiers_boosted_until", table_name="project_dossiers")
    op.drop_index("ix_project_dossiers_user_id", table_name="project_dossiers")
    op.drop_index("ix_project_dossiers_domain_persona", table_name="project_dossiers")
    op.drop_index("ix_project_dossiers_stage", table_name="project_dossiers")
    op.drop_column("project_dossiers", "boosted_until")
    op.drop_column("project_dossiers", "missing_roles_embedding")
    op.drop_column("project_dossiers", "trend_radar_cache")
    op.drop_column("project_dossiers", "stage")

    op.execute("DROP INDEX IF EXISTS idx_users_skills_embedding;")
    op.drop_index("ix_users_active_persona_id", table_name="users")
    op.drop_column("users", "skills_embedding")
    op.drop_column("users", "verified_skills")
    op.drop_column("users", "active_persona_id")
    op.drop_column("users", "city")
    op.drop_column("users", "campus_or_org")
    op.execute("ALTER TABLE users ALTER COLUMN credits_balance SET DEFAULT 50;")
