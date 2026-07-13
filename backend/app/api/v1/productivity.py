"""
TRACE - Productivity, Reporting & Admin Dashboard API Router
Endpoints for AI scoring, weekly reports, admin dashboard, and analytics.
RBAC: All endpoints require Manager/Admin role.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import HTMLResponse

from app.core.permissions import require_manager_or_admin
from app.database import get_db
from app.models.user import User
from app.models.employee import Employee
from app.models.attendance import Attendance
from app.models.task import Task
from app.models.productivity import ProductivityScore
from app.schemas.productivity import ProductivityScoreResponse
from app.services.scoring_service import ScoringService
from app.services.report_service import ReportService

router = APIRouter(tags=["Productivity & Reports"])


# ══════════════════════════════════════════════════════════════════
#  AI SCORING
# ══════════════════════════════════════════════════════════════════

@router.post(
    "/productivity/compute/{employee_id}",
    response_model=ProductivityScoreResponse,
    summary="Compute productivity score",
    description="Trigger the AI scoring engine for a specific employee and week. Admin/Manager only.",
)
async def compute_score(
    employee_id: int,
    week_start: date = Query(..., description="Monday of the target week (YYYY-MM-DD)"),
    current_user: User = Depends(require_manager_or_admin),
    db: AsyncSession = Depends(get_db),
):
    service = ScoringService(db)
    score = await service.compute_weekly_score(employee_id, week_start)
    return ProductivityScoreResponse.model_validate(score)


@router.post(
    "/productivity/compute-all",
    summary="Compute scores for all active employees",
    description="Batch-trigger scoring for every active employee. Admin/Manager only.",
)
async def compute_all_scores(
    week_start: date = Query(..., description="Monday of the target week"),
    current_user: User = Depends(require_manager_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Compute weekly productivity score for all active employees."""
    result = await db.execute(
        select(Employee.id).where(
            Employee.status == "Active", Employee.deleted_at.is_(None)
        )
    )
    employee_ids = [row[0] for row in result.all()]

    service = ScoringService(db)
    computed = []
    errors = []

    for emp_id in employee_ids:
        try:
            score = await service.compute_weekly_score(emp_id, week_start)
            computed.append({
                "employee_id": emp_id,
                "final_score": float(score.final_score) if score.final_score else 0,
                "rating": score.rating,
            })
        except Exception as e:
            errors.append({"employee_id": emp_id, "error": str(e)})

    return {
        "week_start": week_start.isoformat(),
        "computed": len(computed),
        "failed": len(errors),
        "results": computed,
        "errors": errors,
    }


@router.get(
    "/productivity/scores",
    summary="List productivity scores",
    description="Admin/Manager only. Filterable by employee and week.",
)
async def list_scores(
    employee_id: int | None = None,
    week_start: date | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_manager_or_admin),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    conditions = [ProductivityScore.deleted_at.is_(None)]

    if employee_id:
        conditions.append(ProductivityScore.employee_id == employee_id)
    if week_start:
        conditions.append(ProductivityScore.week_start == week_start)

    count = (await db.execute(
        select(func.count(ProductivityScore.id)).where(*conditions)
    )).scalar() or 0

    result = await db.execute(
        select(ProductivityScore)
        .where(*conditions)
        .order_by(ProductivityScore.week_start.desc(), ProductivityScore.final_score.desc())
        .offset(offset)
        .limit(per_page)
    )
    scores = result.scalars().all()

    return {
        "scores": [ProductivityScoreResponse.model_validate(s) for s in scores],
        "total": count,
        "page": page,
        "per_page": per_page,
    }


# ══════════════════════════════════════════════════════════════════
#  REPORTS
# ══════════════════════════════════════════════════════════════════

@router.get(
    "/reports/weekly-summary",
    summary="Weekly productivity summary",
    description="Admin/Manager only.",
)
async def weekly_summary(
    week_start: date | None = None,
    current_user: User = Depends(require_manager_or_admin),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    return await service.generate_weekly_summary(week_start)


@router.get(
    "/reports/attendance-summary",
    summary="Daily attendance summary",
    description="Admin/Manager only. Defaults to today.",
)
async def attendance_summary(
    target_date: date | None = None,
    current_user: User = Depends(require_manager_or_admin),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    return await service.generate_attendance_summary(target_date)


@router.get(
    "/reports/weekly-html",
    response_class=HTMLResponse,
    summary="Weekly report as HTML",
    description="Admin/Manager only. Renderable HTML report (PDF-ready).",
)
async def weekly_report_html(
    week_start: date | None = None,
    current_user: User = Depends(require_manager_or_admin),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    summary = await service.generate_weekly_summary(week_start)
    html = service.generate_report_html(summary)
    return HTMLResponse(content=html)


# ══════════════════════════════════════════════════════════════════
#  ADMIN DASHBOARD
# ══════════════════════════════════════════════════════════════════

@router.get(
    "/dashboard/stats",
    summary="Admin dashboard statistics",
    description="Aggregated system-wide metrics for the admin dashboard. Admin/Manager only.",
)
async def dashboard_stats(
    current_user: User = Depends(require_manager_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns aggregated metrics:
    - Total & active employees
    - Today's attendance count & rate
    - Task status breakdown
    - Average productivity score (current week)
    """
    from datetime import timedelta

    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    # Employee counts
    total_employees = (await db.execute(
        select(func.count(Employee.id)).where(Employee.deleted_at.is_(None))
    )).scalar() or 0

    active_employees = (await db.execute(
        select(func.count(Employee.id)).where(
            Employee.status == "Active", Employee.deleted_at.is_(None)
        )
    )).scalar() or 0

    # Today's attendance
    present_today = (await db.execute(
        select(func.count(Attendance.id)).where(
            Attendance.attendance_date == today,
            Attendance.deleted_at.is_(None),
        )
    )).scalar() or 0

    # Task breakdown
    task_pending = (await db.execute(
        select(func.count(Task.id)).where(
            Task.status == "Pending", Task.deleted_at.is_(None)
        )
    )).scalar() or 0

    task_wip = (await db.execute(
        select(func.count(Task.id)).where(
            Task.status == "WIP", Task.deleted_at.is_(None)
        )
    )).scalar() or 0

    task_completed = (await db.execute(
        select(func.count(Task.id)).where(
            Task.status == "Completed", Task.deleted_at.is_(None)
        )
    )).scalar() or 0

    task_delayed = (await db.execute(
        select(func.count(Task.id)).where(
            Task.status == "Delayed", Task.deleted_at.is_(None)
        )
    )).scalar() or 0

    total_tasks = (await db.execute(
        select(func.count(Task.id)).where(Task.deleted_at.is_(None))
    )).scalar() or 0

    # Average productivity score this week
    avg_score = (await db.execute(
        select(func.avg(ProductivityScore.final_score)).where(
            ProductivityScore.week_start == week_start,
            ProductivityScore.deleted_at.is_(None),
        )
    )).scalar()

    at_risk_count = (await db.execute(
        select(func.count(ProductivityScore.id)).where(
            ProductivityScore.week_start == week_start,
            ProductivityScore.rating == "Risk",
            ProductivityScore.deleted_at.is_(None),
        )
    )).scalar() or 0

    return {
        "date": today.isoformat(),
        "week_start": week_start.isoformat(),
        "employees": {
            "total": total_employees,
            "active": active_employees,
        },
        "attendance": {
            "present_today": present_today,
            "attendance_rate": round(
                (present_today / active_employees * 100), 1
            ) if active_employees > 0 else 0,
        },
        "tasks": {
            "total": total_tasks,
            "pending": task_pending,
            "wip": task_wip,
            "completed": task_completed,
            "delayed": task_delayed,
        },
        "productivity": {
            "avg_score": round(float(avg_score), 2) if avg_score else None,
            "at_risk_count": at_risk_count,
        },
    }
