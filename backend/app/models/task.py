"""
TRACE - Task Management Models
Tables: tasks, task_types, task_details, task_comments, task_time_logs,
        task_discussions (see project.py)
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import BaseModelMixin


class TaskType(BaseModelMixin, Base):
    """
    task_types table — categorizes tasks.
    Values: Bug Fix, Feature Development, Enhancement, Research, Documentation
    """

    __tablename__ = "task_types"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ────────────────────────────────────────────
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="task_type")

    def __repr__(self) -> str:
        return f"<TaskType(id={self.id}, name={self.name})>"


class Task(BaseModelMixin, Base):
    """
    tasks table — core task entity; a task is a GitHub issue (1:1).
    Status: Pending, In Progress, In Review, Completed, Blocked, Overdue, Cancelled
    Priority: Low, Medium, High, Critical

    Phase-1 adds:
      project_id, task_group_id, task_progress_doc,
      assigned_to_user_id, assigned_by_user_id, completed_by, completed_at

    Old tree columns (parent_task_id, team_lead_id, project_manager_id,
    task_level_role, tree_path) are retained until Phase-1 step 5 drops them
    after backfill verification.
    """

    __tablename__ = "tasks"

    # ── Phase-1 new columns ─────────────────────────────────────
    project_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("projects.id"), nullable=True
    )
    task_group_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("task_groups.id"), nullable=True
    )
    task_progress_doc: Mapped[str | None] = mapped_column(String(500), nullable=True)
    progress_doc_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_to_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    assigned_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    completed_by: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # 'Assignee' | 'Project Manager'
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Retained columns ─────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("task_types.id"), nullable=True
    )
    priority: Mapped[str] = mapped_column(
        String(20), default="Medium", nullable=False
    )  # Low, Medium, High, Critical
    impact_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    estimated_hours: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="Pending", nullable=False
    )  # Pending, In Progress, In Review, Completed, Blocked, Overdue, Cancelled
    github_issue_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    github_issue_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    commit_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    commit_hash: Mapped[str | None] = mapped_column(String(100), nullable=True)
    llm_verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    health_score: Mapped[str] = mapped_column(String(20), default="Green", nullable=False)  # Green, Yellow, Red
    health_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_health_check: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationships ────────────────────────────────────────────
    task_type: Mapped[TaskType | None] = relationship("TaskType", back_populates="tasks")
    # New project-model relationships
    project: Mapped["Project | None"] = relationship(
        "Project", foreign_keys=[project_id], back_populates=None
    )
    task_group: Mapped["TaskGroup | None"] = relationship(
        "TaskGroup", foreign_keys=[task_group_id], back_populates="tasks"
    )
    assigned_to_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[assigned_to_user_id]
    )
    assigned_by_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[assigned_by_user_id]
    )
    discussions: Mapped[list["TaskDiscussion"]] = relationship(
        "TaskDiscussion", back_populates="task", cascade="all, delete-orphan"
    )
    # Legacy employee-based assignment comments (no FK columns — dropped in Phase-1)
    task_detail: Mapped["TaskDetail | None"] = relationship(
        "TaskDetail", back_populates="task", uselist=False
    )
    comments: Mapped[list["TaskComment"]] = relationship(
        "TaskComment", back_populates="task"
    )
    time_logs: Mapped[list["TaskTimeLog"]] = relationship(
        "TaskTimeLog", back_populates="task"
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title={self.title}, status={self.status})>"


class TaskDetail(BaseModelMixin, Base):
    """
    task_details table — extended task information.
    """

    __tablename__ = "task_details"

    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tasks.id"), nullable=False
    )
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    acceptance_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ────────────────────────────────────────────
    task: Mapped[Task] = relationship("Task", back_populates="task_detail")

    def __repr__(self) -> str:
        return f"<TaskDetail(id={self.id}, task_id={self.task_id})>"


class TaskComment(BaseModelMixin, Base):
    """
    task_comments table — comments on tasks by employees.
    """

    __tablename__ = "task_comments"

    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tasks.id"), nullable=False
    )
    employee_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("employees.id"), nullable=False
    )
    comment: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Relationships ────────────────────────────────────────────
    task: Mapped[Task] = relationship("Task", back_populates="comments")
    employee: Mapped["Employee"] = relationship("Employee", back_populates="task_comments")

    def __repr__(self) -> str:
        return f"<TaskComment(id={self.id}, task_id={self.task_id})>"


class TaskTimeLog(BaseModelMixin, Base):
    """
    task_time_logs table — tracks start/pause/stop work sessions.
    """

    __tablename__ = "task_time_logs"

    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tasks.id"), nullable=False
    )
    employee_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("employees.id"), nullable=False
    )
    start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    active_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    idle_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Relationships ────────────────────────────────────────────
    task: Mapped[Task] = relationship("Task", back_populates="time_logs")
    employee: Mapped["Employee"] = relationship("Employee", back_populates="task_time_logs")

    def __repr__(self) -> str:
        return f"<TaskTimeLog(id={self.id}, task_id={self.task_id}, active_min={self.active_minutes})>"


# Forward reference imports
from app.models.employee import Employee  # noqa: E402, F401
from app.models.project import Project, TaskGroup, TaskDiscussion  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
