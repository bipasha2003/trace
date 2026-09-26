"""gantt_job_attribution

Revision ID: f3c4d5e6a7b8
Revises: e2b3c4d5f6a7
Create Date: 2026-09-26 13:02:00

CORE.md §2 rule 4 — every Gantt version records the job that wrote it.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = 'f3c4d5e6a7b8'
down_revision = 'e2b3c4d5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('gantt_charts', sa.Column('generated_by_job', sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column('gantt_charts', 'generated_by_job')
