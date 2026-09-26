"""task_group_dependencies

Revision ID: e2b3c4d5f6a7
Revises: d1a2b3c4e5f6
Create Date: 2026-09-26 13:01:00

task_groups.depends_on — the ids of the groups this one waits for (CORE.md §3
step 5, §5.1). Kept on the group so every Gantt re-plan reuses them.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = 'e2b3c4d5f6a7'
down_revision = 'd1a2b3c4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('task_groups', sa.Column('depends_on', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('task_groups', 'depends_on')
