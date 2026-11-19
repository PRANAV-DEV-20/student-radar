"""initial_schema_with_pgvector

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-15 21:38:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector
from pgvector.sqlalchemy import Vector

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 0. Extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    # Some local installs provide pgvector's SQL functions/types directly
    # (e.g. a staged vector.dll) without installing the extension control file.
    # In that case the `vector` type already exists and CREATE EXTENSION would
    # fail, so only call it when the type is missing.
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'vector') THEN
            CREATE EXTENSION IF NOT EXISTS "vector";
          END IF;
        END
        $$;
        """
    )

    # 1. users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=True),
        sa.Column('full_name', sa.String(length=120), nullable=True),
        sa.Column('avatar_url', sa.Text(), nullable=True),
        sa.Column('oauth_provider', sa.String(length=50), server_default='google'),
        sa.Column('oauth_id', sa.String(length=255), nullable=True),
        sa.Column('credits_balance', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # 2. project_dossiers
    op.create_table(
        'project_dossiers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('guest_session_id', sa.String(length=100), nullable=True),
        sa.Column('slug', sa.String(length=150), nullable=False, unique=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('tagline', sa.String(length=300), nullable=False),
        sa.Column('domain_persona', sa.String(length=50), nullable=False),
        sa.Column('problem_statement', sa.Text(), nullable=False),
        sa.Column('solution_breakdown', postgresql.JSONB(), nullable=False),
        sa.Column('tech_stack', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('key_metrics', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('whitespace_analysis', postgresql.JSONB(), nullable=True),
        sa.Column('missing_roles', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('external_links', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('verified_status', sa.Boolean(), server_default='false'),
        sa.Column('boosted', sa.Boolean(), server_default='false'),
        sa.Column('embedding', Vector(768), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    op.create_index('ix_project_dossiers_slug', 'project_dossiers', ['slug'])
    op.create_index('ix_project_dossiers_guest_id', 'project_dossiers', ['guest_session_id'])
    op.execute('CREATE INDEX IF NOT EXISTS idx_dossier_embedding ON project_dossiers USING hnsw (embedding vector_cosine_ops);')

    # 3. pr_assets
    op.create_table(
        'pr_assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('dossier_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('project_dossiers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('asset_type', sa.String(length=50), nullable=False),
        sa.Column('content_json', postgresql.JSONB(), nullable=False),
        sa.Column('og_image_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    # 4. opportunities
    op.create_table(
        'opportunities',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('title', sa.String(length=250), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('canonical_source_url', sa.Text(), nullable=False, unique=True),
        sa.Column('host_organization', sa.String(length=150), nullable=True),
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('tags', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('domain_personas', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('location_type', sa.String(length=50), server_default='virtual'),
        sa.Column('reward_pool', sa.String(length=100), nullable=True),
        sa.Column('embedding', Vector(768), nullable=True),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    op.create_index('ix_opportunities_deadline', 'opportunities', ['deadline'])
    op.execute('CREATE INDEX IF NOT EXISTS idx_opportunity_embedding ON opportunities USING hnsw (embedding vector_cosine_ops);')

    # 5. user_briefings
    op.create_table(
        'user_briefings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('briefing_date', sa.Date(), nullable=False),
        sa.Column('opportunity_ids', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('strongest_pick_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('opportunities.id', ondelete='SET NULL'), nullable=True),
        sa.Column('networking_plan_json', postgresql.JSONB(), nullable=True),
        sa.Column('persona_mode', sa.String(length=50), nullable=False, server_default='tech_builder'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('user_id', 'briefing_date', name='unique_user_briefing_per_day')
    )

    # 6. referral_invites
    op.create_table(
        'referral_invites',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('sender_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('recipient_email_hash', sa.String(length=64), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False, unique=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='pending'),
        sa.Column('claimed_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    op.create_index('ix_referral_invites_recipient_hash', 'referral_invites', ['recipient_email_hash'])

    # 7. suppressed_emails
    op.create_table(
        'suppressed_emails',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('email_hash', sa.String(length=64), nullable=False, unique=True),
        sa.Column('reason', sa.String(length=100), server_default='user_opt_out'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    # 8. credit_transactions
    op.create_table(
        'credit_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(length=50), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'))
    )

def downgrade() -> None:
    op.drop_table('credit_transactions')
    op.drop_table('suppressed_emails')
    op.drop_table('referral_invites')
    op.drop_table('user_briefings')
    op.drop_table('opportunities')
    op.drop_table('pr_assets')
    op.drop_table('project_dossiers')
    op.drop_table('users')

