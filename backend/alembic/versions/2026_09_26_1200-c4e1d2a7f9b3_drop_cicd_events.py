"""drop_cicd_events

Revision ID: c4e1d2a7f9b3
Revises: b9911ce6a96a
Create Date: 2026-09-26 12:00:00

CI/CD-driven completion was removed from the design (PLANNING.md §4): the
assignee marks their own task complete. cicd_events was its webhook audit trail,
never written to; it goes with it. Downgrade recreates the empty table.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'c4e1d2a7f9b3'
down_revision = 'b9911ce6a96a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table('cicd_events')


def downgrade() -> None:
    op.create_table('cicd_events',
    sa.Column('project_id', sa.BigInteger(), nullable=False),
    sa.Column('provider', sa.String(length=50), nullable=True),
    sa.Column('commit_sha', sa.String(length=100), nullable=True),
    sa.Column('commit_message', sa.Text(), nullable=True),
    sa.Column('branch', sa.String(length=255), nullable=True),
    sa.Column('pipeline_status', sa.String(length=30), nullable=True),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('resolved_task_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('ai_reasoning', sa.Text(), nullable=True),
    sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
