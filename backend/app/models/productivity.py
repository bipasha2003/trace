"""
TRACE - Productivity Score Model
Table: productivity_scores
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import BaseModelMixin


class ProductivityScore(BaseModelMixin, Base):
    """
    productivity_scores table — weekly AI-computed scores.
    Rating: Excellent (≥90), Good (75–89), Average (60–74), Risk (<60)
    """

    __tablename__ = "productivity_scores"

    employee_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("employees.id"), nullable=False
    )
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    att_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    task_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    deadline_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    active_time_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    final_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    rating: Mapped[str | None] = mapped_column(
        String(15), nullable=True
    )  # Excellent, Good, Average, Risk
    anomaly_flags: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ────────────────────────────────────────────
    employee: Mapped["Employee"] = relationship(
        "Employee", back_populates="productivity_scores"
    )

    def __repr__(self) -> str:
        return (
            f"<ProductivityScore(id={self.id}, employee_id={self.employee_id}, "
            f"week={self.week_start}, final={self.final_score}, rating={self.rating})>"
        )


# Forward reference import
from app.models.employee import Employee  # noqa: E402, F401
