"""
TRACE - Attendance and TimeZone Models
Tables: attendance, time_zones
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import BaseModelMixin


class TimeZone(BaseModelMixin, Base):
    """
    time_zones table — stores supported time zones.
    """

    __tablename__ = "time_zones"

    timezone_name: Mapped[str] = mapped_column(String(100), nullable=False)
    utc_offset: Mapped[str] = mapped_column(String(20), nullable=False)

    # ── Relationships ────────────────────────────────────────────
    attendance_records: Mapped[list["Attendance"]] = relationship(
        "Attendance", back_populates="time_zone"
    )

    def __repr__(self) -> str:
        return f"<TimeZone(id={self.id}, name={self.timezone_name})>"


class Attendance(BaseModelMixin, Base):
    """
    attendance table — daily attendance records with GPS and time tracking.
    """

    __tablename__ = "attendance"

    employee_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("employees.id"), nullable=False
    )
    time_zone_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("time_zones.id"), nullable=True
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    time_in: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_hours: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    location_status: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # office, remote, suspicious

    # ── Relationships ────────────────────────────────────────────
    employee: Mapped["Employee"] = relationship(
        "Employee", back_populates="attendance_records"
    )
    time_zone: Mapped[TimeZone | None] = relationship(
        "TimeZone", back_populates="attendance_records"
    )

    def __repr__(self) -> str:
        return f"<Attendance(id={self.id}, employee_id={self.employee_id}, date={self.attendance_date})>"


# Forward reference import
from app.models.employee import Employee  # noqa: E402, F401
