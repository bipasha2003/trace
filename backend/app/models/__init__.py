"""
TRACE - Models Package
Imports all models so Alembic and the app can discover them.

Phase-1 completed:
  - New: projects, project_source_files, project_assignments, task_groups,
    gantt_charts, task_discussions, notifications, system_settings, cicd_events
  - New column: users.github_username
  - Altered: tasks — 7 new columns, old tree columns dropped
  - Dropped: project_groups, project_group_messages, evaluation_disputes,
    task_commit_logs, system_menus, role_menu_permissions
  - Roles migrated: Platform Admin → Admin, Staff → Employee
"""

from app.models.base import BaseModelMixin, SoftDeleteMixin, TimestampMixin
from app.models.user import Profile, Role, User, UserRole
from app.models.employee import Department, Designation, Employee, EmployeeDetail, WorkSchedule
from app.models.attendance import Attendance, TimeZone
from app.models.hrms import Leave, Holiday
from app.models.task import Task, TaskComment, TaskDetail, TaskTimeLog, TaskType
from app.models.productivity import ProductivityScore
from app.models.project import (
    Project,
    ProjectSourceFile,
    ProjectAssignment,
    TaskGroup,
    GanttChart,
    TaskDiscussion,
    Notification,
    SystemSetting,
    CicdEvent,
)

__all__ = [
    # Base
    "BaseModelMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
    # User
    "User",
    "Profile",
    "Role",
    "UserRole",
    # Employee
    "Employee",
    "EmployeeDetail",
    "Department",
    "Designation",
    "WorkSchedule",
    # Attendance
    "Attendance",
    "TimeZone",
    # HRMS
    "Leave",
    "Holiday",
    # Task
    "Task",
    "TaskType",
    "TaskDetail",
    "TaskComment",
    "TaskTimeLog",
    # Productivity
    "ProductivityScore",
    # Project (Phase-1 new)
    "Project",
    "ProjectSourceFile",
    "ProjectAssignment",
    "TaskGroup",
    "GanttChart",
    "TaskDiscussion",
    "Notification",
    "SystemSetting",
    "CicdEvent",
]
