"""
TRACE - Task Management Models
Tables: tasks, task_types, task_details, task_comments, task_time_logs
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
    tasks table — core task entity with assignment and tracking.
    Status: WIP, Review, Completed, Failed, Cancelled
    Priority: Low, Medium, High, Critical
    """

    __tablename__ = "tasks"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("task_types.id"), nullable=True
    )
    assigned_to: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("employees.id"), nullable=True
    )
    assigned_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("employees.id"), nullable=True
    )
    parent_task_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("tasks.id"), nullable=True
    )
    priority: Mapped[str] = mapped_column(
        String(20), default="Medium", nullable=False
    )  # Low, Medium, High, Critical
    impact_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    estimated_hours: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="Pending", nullable=False
    )  # Pending, WIP, Review, Completed, Failed, Cancelled, Delayed

    # ── Relationships ────────────────────────────────────────────
    task_type: Mapped[TaskType | None] = relationship("TaskType", back_populates="tasks")
    assignee: Mapped["Employee | None"] = relationship(
        "Employee", foreign_keys=[assigned_to], back_populates="assigned_tasks"
    )
    assigner: Mapped["Employee | None"] = relationship(
        "Employee", foreign_keys=[assigned_by], back_populates="created_tasks"
    )
    parent_task: Mapped["Task | None"] = relationship(
        "Task", remote_side="Task.id", back_populates="sub_tasks"
    )
    sub_tasks: Mapped[list["Task"]] = relationship("Task", back_populates="parent_task")
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


# Forward reference import
from app.models.employee import Employee  # noqa: E402, F401
