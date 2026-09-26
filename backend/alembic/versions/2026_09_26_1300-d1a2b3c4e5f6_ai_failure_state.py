"""ai_failure_state

Revision ID: d1a2b3c4e5f6
Revises: c4e1d2a7f9b3
Create Date: 2026-09-26 13:00:00

CORE.md §2 rule 6 — AI failures are visible. projects.ai_errors holds
{job name: {message, at}}; tasks.progress_doc_error the reason a task's
progress document could not be written.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = 'd1a2b3c4e5f6'
down_revision = 'c4e1d2a7f9b3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('ai_errors', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('tasks', sa.Column('progress_doc_error', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'progress_doc_error')
    op.drop_column('projects', 'ai_errors')
