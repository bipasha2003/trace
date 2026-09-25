"""
TRACE - Employee, Department, WorkSchedule, EmployeeDetail Models
Tables: employees, departments, work_schedules, employee_details
"""

from datetime import date, time

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import BaseModelMixin


class Designation(BaseModelMixin, Base):
    """
    designations table — job roles and designations.
    """

    __tablename__ = "designations"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    employees: Mapped[list["Employee"]] = relationship(
        "Employee", back_populates="designation"
    )

    def __repr__(self) -> str:
        return f"<Designation(id={self.id}, name={self.name})>"



class Department(BaseModelMixin, Base):
    """
    departments table — organizational departments.
    Values: Design, Development, QA, DevOps, HR
    """

    __tablename__ = "departments"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ────────────────────────────────────────────
    employees: Mapped[list["Employee"]] = relationship(
        "Employee", back_populates="department"
    )

    def __repr__(self) -> str:
        return f"<Department(id={self.id}, name={self.name})>"


class WorkSchedule(BaseModelMixin, Base):
    """
    work_schedules table — defines work shift timing.
    """

    __tablename__ = "work_schedules"

    schedule_name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    break_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Relationships ────────────────────────────────────────────
    employees: Mapped[list["Employee"]] = relationship(
        "Employee", back_populates="work_schedule"
    )

    def __repr__(self) -> str:
        return f"<WorkSchedule(id={self.id}, name={self.schedule_name})>"


class EmployeeDetail(BaseModelMixin, Base):
    """
    employee_details table — personal/contact details of employee.
    """

    __tablename__ = "employee_details"

    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(10), nullable=True)
    marital_status: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # ── Relationships ────────────────────────────────────────────
    employee: Mapped["Employee | None"] = relationship(
        "Employee", back_populates="employee_detail", uselist=False
    )

    def __repr__(self) -> str:
        return f"<EmployeeDetail(id={self.id}, city={self.city})>"


class Employee(BaseModelMixin, Base):
    """
    employees table — links user to company structure.
    """

    __tablename__ = "employees"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    employee_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    manager_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("employees.id"), nullable=True
    )
    department_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("departments.id"), nullable=True
    )
    designation_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("designations.id"), nullable=True
    )
    work_schedule_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("work_schedules.id"), nullable=True
    )
    employee_details_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("employee_details.id"), nullable=True
    )
    joining_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="Active", nullable=False
    )  # Active, Inactive, Blocked

    # ── Relationships ────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="employee")
    manager: Mapped["Employee | None"] = relationship(
        "Employee", remote_side="Employee.id", back_populates="subordinates"
    )
    subordinates: Mapped[list["Employee"]] = relationship(
        "Employee", back_populates="manager"
    )
    department: Mapped[Department | None] = relationship(
        "Department", back_populates="employees"
    )
    designation: Mapped[Designation | None] = relationship(
        "Designation", back_populates="employees"
    )
    work_schedule: Mapped[WorkSchedule | None] = relationship(
        "WorkSchedule", back_populates="employees"
    )
    employee_detail: Mapped[EmployeeDetail | None] = relationship(
        "EmployeeDetail", back_populates="employee", lazy="joined"
    )
    attendance_records: Mapped[list["Attendance"]] = relationship(
        "Attendance", back_populates="employee"
    )
    task_time_logs: Mapped[list["TaskTimeLog"]] = relationship(
        "TaskTimeLog", back_populates="employee"
    )
    task_comments: Mapped[list["TaskComment"]] = relationship(
        "TaskComment", back_populates="employee"
    )
    productivity_scores: Mapped[list["ProductivityScore"]] = relationship(
        "ProductivityScore", back_populates="employee"
    )

    def __repr__(self) -> str:
        return f"<Employee(id={self.id}, code={self.employee_code})>"


# Forward reference imports
from app.models.user import User  # noqa: E402, F401
from app.models.attendance import Attendance  # noqa: E402, F401
from app.models.task import Task, TaskTimeLog, TaskComment  # noqa: E402, F401
from app.models.productivity import ProductivityScore  # noqa: E402, F401
