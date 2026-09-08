"""
TRACE - Models Package
Imports all models so Alembic and the app can discover them.
"""

from app.models.base import BaseModelMixin, SoftDeleteMixin, TimestampMixin
from app.models.user import Profile, Role, User, UserRole
from app.models.employee import Department, Designation, Employee, EmployeeDetail, RoleMenuPermission, SystemMenu, WorkSchedule
from app.models.attendance import Attendance, TimeZone
from app.models.hrms import Leave, Holiday
from app.models.task import Task, TaskComment, TaskDetail, TaskTimeLog, TaskType, ProjectGroup, ProjectGroupMessage, EvaluationDispute, TaskCommitLog
from app.models.productivity import ProductivityScore

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
    "RoleMenuPermission",
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
    "ProjectGroup",
    "ProjectGroupMessage",
    # Productivity
    "ProductivityScore",
]
