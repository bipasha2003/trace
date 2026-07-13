"""
TRACE - Productivity Score Schemas
Pydantic models for AI-generated productivity metrics.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class ProductivityScoreResponse(BaseModel):
    id: int
    employee_id: int
    week_start: date
    att_score: Decimal | None = None
    task_score: Decimal | None = None
    deadline_score: Decimal | None = None
    active_time_score: Decimal | None = None
    final_score: Decimal | None = None
    rating: str | None = None  # Excellent, Good, Average, Risk
    anomaly_flags: dict[str, Any] | None = None
    generated_at: datetime | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProductivityScoreListResponse(BaseModel):
    scores: list[ProductivityScoreResponse]
    total: int
    page: int
    per_page: int


class ProductivitySummary(BaseModel):
    """Weekly summary for admin dashboard."""
    total_employees: int
    average_score: Decimal | None = None
    top_performer: ProductivityScoreResponse | None = None
    at_risk_employees: list[ProductivityScoreResponse] = []
    excellent_count: int = 0
    good_count: int = 0
    average_count: int = 0
    risk_count: int = 0
