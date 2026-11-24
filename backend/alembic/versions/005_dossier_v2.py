"""Dossier v2: research runs, evidence, section content, reviews and versions.

Revision ID: 005_dossier_v2
Revises: 004_ecosystem_benchmark

The create calls are checkfirst so this revision can be stamped cleanly on a
database where the ORM metadata was applied directly during local development.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005_dossier_v2"
down_revision = "004_ecosystem_benchmark"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())


def _create_table(name: str, *columns: sa.Column, **kwargs) -> None:
    if not sa.inspect(op.get_bind()).has_table(name):
        op.create_table(name, *columns, **kwargs)


def _create_index(name: str, table: str, columns: list[str]) -> None:
    if name not in {idx["name"] for idx in sa.inspect(op.get_bind()).get_indexes(table)}:
        op.create_index(name, table, columns)


def upgrade() -> None:
    _create_table(
        "dossier_runs",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("project_id", UUID, sa.ForeignKey("project_dossiers.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("guest_session_id", sa.String(100), nullable=True, index=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("mode", sa.String(10), nullable=False, server_default="deep"),
        sa.Column("input_type", sa.String(20), nullable=False),
        sa.Column("raw_content", sa.Text(), nullable=False),
        sa.Column("domain_persona", sa.String(50), nullable=False, server_default="tech_builder"),
        sa.Column("profile", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("project_dna", JSONB, nullable=True),
        sa.Column("plan", JSONB, nullable=True),
        sa.Column("coverage", JSONB, nullable=True),
        sa.Column("progress", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("tasks", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(10, 4), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )

    _create_table(
        "ai_runs",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("run_id", UUID, sa.ForeignKey("dossier_runs.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("model", sa.String(80), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cached", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    _create_index("ix_ai_runs_run_role", "ai_runs", ["run_id", "role"])

    _create_table(
        "evidence",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("run_id", UUID, sa.ForeignKey("dossier_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("ref", sa.String(20), nullable=False),
        sa.Column("question_id", sa.String(30), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("source_quality", sa.String(30), nullable=True),
        sa.Column("passage", sa.Text(), nullable=False),
        sa.Column("relevance", sa.SmallInteger(), nullable=True),
        sa.Column("canonical_key", sa.String(500), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("run_id", "ref", name="uq_evidence_run_ref"),
    )
    _create_index("ix_evidence_run_question", "evidence", ["run_id", "question_id"])

    _create_table(
        "section_reviews",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("run_id", UUID, sa.ForeignKey("dossier_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("section", sa.String(60), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("failures", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    _create_index("ix_section_reviews_run_section", "section_reviews", ["run_id", "section", "attempt"])

    _create_table(
        "dossier_sections",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("run_id", UUID, sa.ForeignKey("dossier_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("section", sa.String(60), nullable=False),
        sa.Column("content", JSONB, nullable=False),
        sa.Column("confidence", sa.String(10), nullable=True),
        sa.Column("coverage", sa.String(10), nullable=True),
        sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("run_id", "section", name="uq_dossier_sections_run_section"),
    )

    _create_table(
        "dossier_sources",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("run_id", UUID, sa.ForeignKey("dossier_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("ref", sa.String(20), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("source_quality", sa.String(30), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("run_id", "ref", name="uq_dossier_sources_run_ref"),
    )

    _create_table(
        "dossier_versions",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("run_id", UUID, sa.ForeignKey("dossier_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("run_id", "version", name="uq_dossier_versions_run_version"),
    )


def downgrade() -> None:
    for table in (
        "ai_runs",
        "dossier_versions",
        "dossier_sources",
        "dossier_sections",
        "section_reviews",
        "evidence",
        "dossier_runs",
    ):
        if sa.inspect(op.get_bind()).has_table(table):
            op.drop_table(table)
