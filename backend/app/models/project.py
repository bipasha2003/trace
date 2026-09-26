"""
TRACE - Project Models
Tables: projects, project_source_files, project_assignments,
        task_groups, gantt_charts, task_discussions,
        notifications, system_settings
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import BaseModelMixin


class Project(BaseModelMixin, Base):
    """
    projects table — the core project entity.
    Owned by a Manager; contains source docs, four living markdown docs,
    a GitHub repo, task groups and a Gantt chart.
    Status: Draft, Evaluating, Active, Completed, Archived
    """

    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    github_repo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    github_default_branch: Mapped[str] = mapped_column(
        String(100), default="main", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="Draft", nullable=False
    )  # Draft, Evaluating, Active, Completed, Archived
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Document URLs — GitHub repo file URLs; never markdown bodies
    project_initial_doc: Mapped[str | None] = mapped_column(String(500), nullable=True)
    project_doc: Mapped[str | None] = mapped_column(String(500), nullable=True)
    project_progress_doc: Mapped[str | None] = mapped_column(String(500), nullable=True)
    project_report_doc: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_evaluated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────
    created_by: Mapped["User"] = relationship(
        "User", foreign_keys=[created_by_user_id]
    )
    source_files: Mapped[list["ProjectSourceFile"]] = relationship(
        "ProjectSourceFile", back_populates="project", cascade="all, delete-orphan"
    )
    assignments: Mapped[list["ProjectAssignment"]] = relationship(
        "ProjectAssignment", back_populates="project", cascade="all, delete-orphan"
    )
    task_groups: Mapped[list["TaskGroup"]] = relationship(
        "TaskGroup", back_populates="project", cascade="all, delete-orphan"
    )
    gantt_charts: Mapped[list["GanttChart"]] = relationship(
        "GanttChart", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name}, status={self.status})>"


class ProjectSourceFile(BaseModelMixin, Base):
    """
    project_source_files table — binary requirement documents stored in MinIO.
    extracted_text is populated at upload time so the AI need not re-parse.
    """

    __tablename__ = "project_source_files"

    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects.id"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)  # MinIO key
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────
    project: Mapped[Project] = relationship("Project", back_populates="source_files")
    uploaded_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[uploaded_by_user_id]
    )

    def __repr__(self) -> str:
        return f"<ProjectSourceFile(id={self.id}, file={self.file_name})>"


class ProjectAssignment(BaseModelMixin, Base):
    """
    project_assignments table — who is on a project and in what role.
    The single source of truth for project-scoped authorisation.
    project_role: 'Project Manager' or 'Member'
    """

    __tablename__ = "project_assignments"

    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    project_role: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # Project Manager | Member
    assigned_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_user"),
    )

    # ── Relationships ─────────────────────────────────────────────
    project: Mapped[Project] = relationship("Project", back_populates="assignments")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    assigned_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[assigned_by_user_id]
    )

    def __repr__(self) -> str:
        return f"<ProjectAssignment(project={self.project_id}, user={self.user_id}, role={self.project_role})>"


class TaskGroup(BaseModelMixin, Base):
    """
    task_groups table — one Gantt module / planning unit.
    A project has many task groups; a task group has many tasks.
    Status: Pending, In Progress, Completed, Blocked
    """

    __tablename__ = "task_groups"

    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    planned_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    planned_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completion_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=0.0, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="Pending", nullable=False
    )  # Pending, In Progress, Completed, Blocked
    created_by: Mapped[str] = mapped_column(
        String(20), default="Human", nullable=False
    )  # AI | Human

    # ── Relationships ─────────────────────────────────────────────
    project: Mapped[Project] = relationship("Project", back_populates="task_groups")
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="task_group", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TaskGroup(id={self.id}, name={self.name}, project={self.project_id})>"


class GanttChart(BaseModelMixin, Base):
    """
    gantt_charts table — materialised Gantt payload, regenerated as new versions.
    Never patched; the newest version is live.
    generated_reason: initial | task_status_change | project_doc_updated | manual
    """

    __tablename__ = "gantt_charts"

    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    chart_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    generated_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────
    project: Mapped[Project] = relationship("Project", back_populates="gantt_charts")

    def __repr__(self) -> str:
        return f"<GanttChart(id={self.id}, project={self.project_id}, v={self.version})>"


class TaskDiscussion(BaseModelMixin, Base):
    """
    task_discussions table — per-task threaded discussion.
    Visible to: task's assignee, its assigner, the project's Project Managers,
    and the owning Manager.
    """

    __tablename__ = "task_discussions"

    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tasks.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("task_discussions.id"), nullable=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Relationships ─────────────────────────────────────────────
    task: Mapped["Task"] = relationship("Task", back_populates="discussions")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    parent: Mapped["TaskDiscussion | None"] = relationship(
        "TaskDiscussion", remote_side="TaskDiscussion.id", back_populates="replies"
    )
    replies: Mapped[list["TaskDiscussion"]] = relationship(
        "TaskDiscussion", back_populates="parent"
    )

    def __repr__(self) -> str:
        return f"<TaskDiscussion(id={self.id}, task={self.task_id})>"


class Notification(BaseModelMixin, Base):
    """
    notifications table — in-app notifications for all user types.
    type: task_assigned | task_due | task_completed | discussion_reply | project_evaluated
    """

    __tablename__ = "notifications"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    related_task_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("tasks.id"), nullable=True
    )
    related_project_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("projects.id"), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    related_task: Mapped["Task | None"] = relationship(
        "Task", foreign_keys=[related_task_id]
    )
    related_project: Mapped[Project | None] = relationship(
        "Project", foreign_keys=[related_project_id]
    )

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, user={self.user_id}, type={self.type})>"


class SystemSetting(BaseModelMixin, Base):
    """
    system_settings table — runtime configuration, backing Admin → Configuration.
    category: mail | ai | github
    Secrets are encrypted and never returned; resolution order: DB value, then .env fallback.
    """

    __tablename__ = "system_settings"

    category: Mapped[str] = mapped_column(String(50), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("category", "key", name="uq_setting_category_key"),
    )

    def __repr__(self) -> str:
        return f"<SystemSetting(category={self.category}, key={self.key})>"


# Forward references
from app.models.user import User  # noqa: E402, F401
from app.models.task import Task  # noqa: E402, F401
