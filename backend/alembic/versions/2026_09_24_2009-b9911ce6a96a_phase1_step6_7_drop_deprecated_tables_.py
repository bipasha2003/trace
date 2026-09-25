"""phase1_step6_7_drop_deprecated_tables_and_migrate_roles

Revision ID: b9911ce6a96a
Revises: 33090db912ce
Create Date: 2026-09-24 20:09:08

Phase-1 steps 6 & 7:
  6. Drop deprecated tables (project_groups, project_group_messages,
     evaluation_disputes, task_commit_logs, system_menus, role_menu_permissions)
     alongside their model-class removal.
  7. Migrate role rows: 'Platform Admin' → 'Admin', 'Staff' → 'Employee'.
     Repoint user_roles, then delete the obsolete role rows.
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'b9911ce6a96a'
down_revision = '33090db912ce'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ----------------------------------------------------------------
    # Step 6 — Drop deprecated tables (dependencies first)
    # ----------------------------------------------------------------

    # project_group_messages depends on project_groups
    op.drop_table('project_group_messages')
    op.drop_table('project_groups')

    # evaluation_disputes and task_commit_logs depend on tasks
    op.drop_table('evaluation_disputes')
    op.drop_table('task_commit_logs')

    # role_menu_permissions and system_menus are standalone
    op.drop_table('role_menu_permissions')
    op.drop_table('system_menus')

    # ----------------------------------------------------------------
    # Step 7 — Migrate legacy roles
    # ----------------------------------------------------------------

    # Get IDs for target roles (already exist from Phase-0 seeds)
    admin_role = conn.execute(text(
        "SELECT id FROM roles WHERE role_name = 'Admin' LIMIT 1"
    )).fetchone()
    employee_role = conn.execute(text(
        "SELECT id FROM roles WHERE role_name = 'Employee' LIMIT 1"
    )).fetchone()

    if admin_role and employee_role:
        admin_id = admin_role[0]
        employee_id = employee_role[0]

        # Re-point 'Platform Admin' users → 'Admin'
        platform_admin_role = conn.execute(text(
            "SELECT id FROM roles WHERE role_name = 'Platform Admin' LIMIT 1"
        )).fetchone()
        if platform_admin_role:
            pa_id = platform_admin_role[0]
            # Move user_roles rows (avoid duplicates)
            conn.execute(text("""
                UPDATE user_roles SET role_id = :admin_id
                WHERE role_id = :pa_id
                AND NOT EXISTS (
                    SELECT 1 FROM user_roles ur2
                    WHERE ur2.user_id = user_roles.user_id
                    AND ur2.role_id = :admin_id
                )
            """), {"admin_id": admin_id, "pa_id": pa_id})
            conn.execute(text(
                "DELETE FROM user_roles WHERE role_id = :pa_id"
            ), {"pa_id": pa_id})
            conn.execute(text(
                "DELETE FROM roles WHERE id = :pa_id"
            ), {"pa_id": pa_id})

        # Re-point 'Staff' users → 'Employee'
        staff_role = conn.execute(text(
            "SELECT id FROM roles WHERE role_name = 'Staff' LIMIT 1"
        )).fetchone()
        if staff_role:
            staff_id = staff_role[0]
            conn.execute(text("""
                UPDATE user_roles SET role_id = :emp_id
                WHERE role_id = :staff_id
                AND NOT EXISTS (
                    SELECT 1 FROM user_roles ur2
                    WHERE ur2.user_id = user_roles.user_id
                    AND ur2.role_id = :emp_id
                )
            """), {"emp_id": employee_id, "staff_id": staff_id})
            conn.execute(text(
                "DELETE FROM user_roles WHERE role_id = :staff_id"
            ), {"staff_id": staff_id})
            conn.execute(text(
                "DELETE FROM roles WHERE id = :staff_id"
            ), {"staff_id": staff_id})


def downgrade() -> None:
    # Re-create tables (empty; data is not recoverable)
    op.create_table(
        'system_menus',
        *[
            __import__('sqlalchemy', fromlist=['Column']).Column(
                c, t, **kw
            ) for c, t, kw in [
                ('id', __import__('sqlalchemy').BigInteger(), {'primary_key': True, 'autoincrement': True}),
                ('key', __import__('sqlalchemy').String(50), {'nullable': False, 'unique': True}),
                ('label', __import__('sqlalchemy').String(100), {'nullable': False}),
                ('icon', __import__('sqlalchemy').String(50), {'nullable': True}),
                ('is_custom', __import__('sqlalchemy').Boolean(), {'nullable': False, 'default': True}),
                ('created_at', __import__('sqlalchemy').DateTime(timezone=True), {'nullable': False}),
                ('updated_at', __import__('sqlalchemy').DateTime(timezone=True), {'nullable': True}),
                ('deleted_at', __import__('sqlalchemy').DateTime(timezone=True), {'nullable': True}),
            ]
        ]
    )
