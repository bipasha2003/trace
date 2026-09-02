"""
TRACE - HRMS Models (Leaves and Holidays)
Tables: leaves, holidays
"""

from datetime import date
from sqlalchemy import BigInteger, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import BaseModelMixin


class Leave(BaseModelMixin, Base):
    """
    leaves table — tracks employee leave applications & approvals.
    Status: Pending, Approved, Rejected, Cancelled
    Types: Casual, Sick, Earned, Unpaid
    """

    __tablename__ = "leaves"

    employee_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("employees.id"), nullable=False
    )
    leave_type: Mapped[str] = mapped_column(
        String(50), default="Casual", nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="Pending", nullable=False
    )
    approved_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("employees.id"), nullable=True
    )

    # ── Relationships ────────────────────────────────────────────
    employee: Mapped["Employee"] = relationship(
        "Employee", foreign_keys=[employee_id]
    )
    approver: Mapped["Employee | None"] = relationship(
        "Employee", foreign_keys=[approved_by]
    )

    def __repr__(self) -> str:
        return f"<Leave(id={self.id}, employee_id={self.employee_id}, type={self.leave_type}, status={self.status})>"


class Holiday(BaseModelMixin, Base):
    """
    holidays table — company and public holiday calendar.
    """

    __tablename__ = "holidays"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    holiday_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(
        String(50), default="Public", nullable=False
    )  # Public, Optional, Company

    def __repr__(self) -> str:
        return f"<Holiday(id={self.id}, name={self.name}, date={self.holiday_date})>"


from app.models.employee import Employee  # noqa: E402, F401
