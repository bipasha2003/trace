"""
TRACE - Report Service
Generates weekly PDF reports and dispatches via email.
Uses WeasyPrint for PDF generation and SendGrid for email dispatch.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.employee import Employee
from app.models.productivity import ProductivityScore
from app.models.user import User


class ReportService:
    """Generates productivity reports and dispatches via email."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_weekly_summary(
        self, week_start: date | None = None
    ) -> dict[str, Any]:
        """
        Generate a weekly productivity summary for the admin dashboard.

        Report contents (per synopsis):
        - Attendance summary
        - Top performer
        - At-risk employees
        - Delayed task count
        - Average score
        """
        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())

        # Fetch all scores for this week
        stmt = (
            select(ProductivityScore)
            .where(
                ProductivityScore.week_start == week_start,
                ProductivityScore.deleted_at.is_(None),
            )
            .options(
                selectinload(ProductivityScore.employee)
                .selectinload(Employee.user)
            )
            .order_by(ProductivityScore.final_score.desc())
        )
        result = await self.db.execute(stmt)
        scores = result.scalars().all()

        if not scores:
            return {
                "week_start": week_start.isoformat(),
                "total_employees": 0,
                "average_score": None,
                "top_performer": None,
                "at_risk_employees": [],
                "rating_distribution": {
                    "Excellent": 0,
                    "Good": 0,
                    "Average": 0,
                    "Risk": 0,
                },
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        # Compute summary
        total = len(scores)
        avg_score = sum(
            float(s.final_score) for s in scores if s.final_score
        ) / total

        # Rating distribution
        distribution = {"Excellent": 0, "Good": 0, "Average": 0, "Risk": 0}
        for s in scores:
            if s.rating and s.rating in distribution:
                distribution[s.rating] += 1

        # Top performer (highest score)
        top = scores[0] if scores else None
        top_performer = None
        if top and top.employee and top.employee.user:
            top_performer = {
                "employee_id": top.employee_id,
                "name": top.employee.user.name,
                "employee_code": top.employee.employee_code,
                "final_score": float(top.final_score) if top.final_score else 0,
                "rating": top.rating,
            }

        # At-risk employees (score < 60)
        at_risk = []
        for s in scores:
            if s.final_score and float(s.final_score) < 60:
                emp_name = s.employee.user.name if s.employee and s.employee.user else "Unknown"
                emp_code = s.employee.employee_code if s.employee else "N/A"
                at_risk.append({
                    "employee_id": s.employee_id,
                    "name": emp_name,
                    "employee_code": emp_code,
                    "final_score": float(s.final_score),
                    "rating": s.rating,
                    "anomaly_flags": s.anomaly_flags or {},
                })

        return {
            "week_start": week_start.isoformat(),
            "total_employees": total,
            "average_score": round(avg_score, 2),
            "top_performer": top_performer,
            "at_risk_employees": at_risk,
            "at_risk_count": len(at_risk),
            "rating_distribution": distribution,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def generate_attendance_summary(
        self, target_date: date | None = None
    ) -> dict[str, Any]:
        """
        Generate a daily attendance summary for admin.
        Triggered end of workday via Celery.
        """
        from app.models.attendance import Attendance

        if target_date is None:
            target_date = date.today()

        # Total employees
        total_emp = (
            await self.db.execute(
                select(func.count(Employee.id)).where(
                    Employee.status == "Active", Employee.deleted_at.is_(None)
                )
            )
        ).scalar() or 0

        # Present today
        present = (
            await self.db.execute(
                select(func.count(Attendance.id)).where(
                    Attendance.attendance_date == target_date,
                    Attendance.deleted_at.is_(None),
                )
            )
        ).scalar() or 0

        # Location breakdown
        office_count = (
            await self.db.execute(
                select(func.count(Attendance.id)).where(
                    Attendance.attendance_date == target_date,
                    Attendance.location_status == "office",
                    Attendance.deleted_at.is_(None),
                )
            )
        ).scalar() or 0

        remote_count = (
            await self.db.execute(
                select(func.count(Attendance.id)).where(
                    Attendance.attendance_date == target_date,
                    Attendance.location_status == "remote",
                    Attendance.deleted_at.is_(None),
                )
            )
        ).scalar() or 0

        suspicious_count = (
            await self.db.execute(
                select(func.count(Attendance.id)).where(
                    Attendance.attendance_date == target_date,
                    Attendance.location_status == "suspicious",
                    Attendance.deleted_at.is_(None),
                )
            )
        ).scalar() or 0

        absent = total_emp - present

        return {
            "date": target_date.isoformat(),
            "total_employees": total_emp,
            "present": present,
            "absent": absent,
            "attendance_rate": round((present / total_emp * 100), 1) if total_emp > 0 else 0,
            "location_breakdown": {
                "office": office_count,
                "remote": remote_count,
                "suspicious": suspicious_count,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def generate_report_html(self, summary: dict[str, Any]) -> str:
        """
        Generate structured HTML report content.
        This HTML can be converted to PDF via WeasyPrint in future.
        """
        at_risk_rows = ""
        for emp in summary.get("at_risk_employees", []):
            at_risk_rows += f"""
            <tr>
                <td>{emp['employee_code']}</td>
                <td>{emp['name']}</td>
                <td>{emp['final_score']}</td>
                <td>{emp['rating']}</td>
            </tr>"""

        top = summary.get("top_performer") or {}
        dist = summary.get("rating_distribution", {})

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>TRACE Weekly Performance Report</title>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #333; }}
                h1 {{ color: #1a237e; border-bottom: 3px solid #1a237e; padding-bottom: 10px; }}
                h2 {{ color: #283593; margin-top: 30px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
                th {{ background: #1a237e; color: white; }}
                tr:nth-child(even) {{ background: #f5f5f5; }}
                .metric {{ display: inline-block; padding: 15px 25px; margin: 8px;
                           background: #e8eaf6; border-radius: 8px; text-align: center; }}
                .metric .value {{ font-size: 28px; font-weight: bold; color: #1a237e; }}
                .metric .label {{ font-size: 12px; color: #666; margin-top: 4px; }}
                .risk {{ color: #c62828; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>📊 TRACE Weekly Performance Report</h1>
            <p><strong>Week Starting:</strong> {summary.get('week_start', 'N/A')}</p>
            <p><strong>Generated:</strong> {summary.get('generated_at', 'N/A')}</p>

            <div>
                <div class="metric">
                    <div class="value">{summary.get('total_employees', 0)}</div>
                    <div class="label">Total Employees</div>
                </div>
                <div class="metric">
                    <div class="value">{summary.get('average_score', 'N/A')}</div>
                    <div class="label">Avg Score</div>
                </div>
                <div class="metric">
                    <div class="value">{dist.get('Excellent', 0)}</div>
                    <div class="label">Excellent</div>
                </div>
                <div class="metric">
                    <div class="value">{dist.get('Good', 0)}</div>
                    <div class="label">Good</div>
                </div>
                <div class="metric">
                    <div class="value">{dist.get('Average', 0)}</div>
                    <div class="label">Average</div>
                </div>
                <div class="metric">
                    <div class="value risk">{dist.get('Risk', 0)}</div>
                    <div class="label">At Risk</div>
                </div>
            </div>

            <h2>🏆 Top Performer</h2>
            <p><strong>{top.get('name', 'N/A')}</strong> ({top.get('employee_code', '')})
            — Score: {top.get('final_score', 'N/A')} ({top.get('rating', '')})</p>

            <h2>⚠️ At-Risk Employees (Score &lt; 60)</h2>
            <table>
                <tr><th>Code</th><th>Name</th><th>Score</th><th>Rating</th></tr>
                {at_risk_rows if at_risk_rows else '<tr><td colspan="4">No at-risk employees this week 🎉</td></tr>'}
            </table>
        </body>
        </html>
        """
        return html
