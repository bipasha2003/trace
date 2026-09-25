"""phase1_step4_5_backfill_tree_into_projects_and_drop_tree_cols

Revision ID: 33090db912ce
Revises: 095aa996a973
Create Date: 2026-09-24 20:06:08

Phase-1 steps 4 & 5:
  4. Backfill existing seeded task tree → projects / task_groups / tasks
     • Tasks with parent_task_id IS NULL become Projects
     • Depth-1 children become TaskGroups under those projects
     • Deeper children are flattened to the nearest group
  5. Drop tree columns (parent_task_id, team_lead_id, project_manager_id,
     task_level_role, tree_path) now that backfill is verified.
     Drop also assigned_to / assigned_by (legacy employee FK) now superseded
     by assigned_to_user_id / assigned_by_user_id on users.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '33090db912ce'
down_revision = '095aa996a973'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ----------------------------------------------------------------
    # Step 4 — Backfill
    # ----------------------------------------------------------------

    # Find the first Admin-role user to act as the project creator
    admin_row = conn.execute(text("""
        SELECT u.id FROM users u
        JOIN user_roles ur ON ur.user_id = u.id
        JOIN roles r ON r.id = ur.role_id
        WHERE r.role_name IN ('Admin', 'Manager')
        ORDER BY u.id LIMIT 1
    """)).fetchone()

    creator_id = admin_row[0] if admin_row else None

    # Fetch all root tasks (no parent)
    root_tasks = conn.execute(text("""
        SELECT id, title, description, status, due_date, created_at
        FROM tasks
        WHERE parent_task_id IS NULL
        AND deleted_at IS NULL
    """)).fetchall()

    for root in root_tasks:
        root_id = root[0]
        root_title = root[1]
        root_desc = root[2]
        root_created = root[5]

        # Insert project row
        proj = conn.execute(text("""
            INSERT INTO projects
              (name, description, created_by_user_id, github_default_branch, status, created_at, updated_at)
            VALUES
              (:name, :desc, :creator, 'main', 'Draft', :created_at, now())
            RETURNING id
        """), {
            "name": root_title,
            "desc": root_desc,
            "creator": creator_id,
            "created_at": root_created,
        }).fetchone()
        project_id = proj[0]

        # Link the root task itself to this project
        conn.execute(text("""
            UPDATE tasks SET project_id = :pid WHERE id = :tid
        """), {"pid": project_id, "tid": root_id})

        # Fetch depth-1 children → become task groups
        depth1 = conn.execute(text("""
            SELECT id, title, description, status, due_date, created_at
            FROM tasks
            WHERE parent_task_id = :root
            AND deleted_at IS NULL
        """), {"root": root_id}).fetchall()

        for seq, child in enumerate(depth1, start=1):
            child_id = child[0]
            child_title = child[1]
            child_desc = child[2]
            child_created = child[5]

            # Create task group
            grp = conn.execute(text("""
                INSERT INTO task_groups
                  (project_id, name, description, sequence, completion_percentage, status, created_by, created_at, updated_at)
                VALUES
                  (:pid, :name, :desc, :seq, 0.0, 'Pending', 'Human', :created_at, now())
                RETURNING id
            """), {
                "pid": project_id,
                "name": child_title,
                "desc": child_desc,
                "seq": seq,
                "created_at": child_created,
            }).fetchone()
            group_id = grp[0]

            # Link depth-1 child to this project + group (it stays as a task too)
            conn.execute(text("""
                UPDATE tasks
                SET project_id = :pid, task_group_id = :gid
                WHERE id = :tid
            """), {"pid": project_id, "gid": group_id, "tid": child_id})

            # Flatten all deeper descendants into this group
            conn.execute(text("""
                WITH RECURSIVE descendants AS (
                    SELECT id FROM tasks WHERE parent_task_id = :child_id
                    UNION ALL
                    SELECT t.id FROM tasks t
                    JOIN descendants d ON t.parent_task_id = d.id
                )
                UPDATE tasks
                SET project_id = :pid, task_group_id = :gid
                WHERE id IN (SELECT id FROM descendants)
            """), {"child_id": child_id, "pid": project_id, "gid": group_id})

    # ----------------------------------------------------------------
    # Step 5 — Drop legacy tree columns (PostgreSQL — no batch needed)
    # ----------------------------------------------------------------
    op.drop_constraint('tasks_parent_task_id_fkey', 'tasks', type_='foreignkey')
    op.drop_constraint('tasks_team_lead_id_fkey', 'tasks', type_='foreignkey')
    op.drop_constraint('tasks_project_manager_id_fkey', 'tasks', type_='foreignkey')
    op.drop_constraint('tasks_assigned_to_fkey', 'tasks', type_='foreignkey')
    op.drop_constraint('tasks_assigned_by_fkey', 'tasks', type_='foreignkey')

    op.drop_column('tasks', 'parent_task_id')
    op.drop_column('tasks', 'team_lead_id')
    op.drop_column('tasks', 'project_manager_id')
    op.drop_column('tasks', 'task_level_role')
    op.drop_column('tasks', 'tree_path')
    op.drop_column('tasks', 'assigned_to')
    op.drop_column('tasks', 'assigned_by')


def downgrade() -> None:
    # Re-add dropped columns (data cannot be restored automatically)
    with op.batch_alter_table('tasks') as batch_op:
        batch_op.add_column(sa.Column('parent_task_id', sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column('team_lead_id', sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column('project_manager_id', sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column('task_level_role', sa.String(50), nullable=False, server_default='Member'))
        batch_op.add_column(sa.Column('tree_path', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('assigned_to', sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column('assigned_by', sa.BigInteger(), nullable=True))
