"""
TRACE - Database Seed Script
Populates initial reference data: roles, departments, task types,
work schedules, and time zones.

Usage:
    python -m app.seeds
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.attendance import TimeZone
from app.models.employee import Department, WorkSchedule
from app.models.task import TaskType
from app.models.user import Role


# ── Reference Data ───────────────────────────────────────────────

ROLES = ["Admin", "Manager", "Staff"]

DEPARTMENTS = [
    {"name": "Design", "description": "UI/UX and graphic design team"},
    {"name": "Development", "description": "Software development and engineering"},
    {"name": "QA", "description": "Quality assurance and testing"},
    {"name": "DevOps", "description": "Infrastructure and deployment operations"},
    {"name": "HR", "description": "Human resources and people operations"},
]

TASK_TYPES = [
    {"name": "Bug Fix", "description": "Fixing reported bugs and issues"},
    {"name": "Feature Development", "description": "Building new features"},
    {"name": "Enhancement", "description": "Improving existing functionality"},
    {"name": "Research", "description": "Research and investigation tasks"},
    {"name": "Documentation", "description": "Writing or updating documentation"},
]

WORK_SCHEDULES = [
    {"schedule_name": "Standard (9-6)", "start_time": "09:00", "end_time": "18:00", "break_minutes": 60},
    {"schedule_name": "Early (7-4)", "start_time": "07:00", "end_time": "16:00", "break_minutes": 60},
    {"schedule_name": "Late (11-8)", "start_time": "11:00", "end_time": "20:00", "break_minutes": 60},
    {"schedule_name": "Night (22-7)", "start_time": "22:00", "end_time": "07:00", "break_minutes": 60},
    {"schedule_name": "Flexi (10-7)", "start_time": "10:00", "end_time": "19:00", "break_minutes": 60},
]

TIME_ZONES = [
    {"timezone_name": "Asia/Kolkata", "utc_offset": "+05:30"},
    {"timezone_name": "America/New_York", "utc_offset": "-05:00"},
    {"timezone_name": "America/Los_Angeles", "utc_offset": "-08:00"},
    {"timezone_name": "Europe/London", "utc_offset": "+00:00"},
    {"timezone_name": "Asia/Tokyo", "utc_offset": "+09:00"},
    {"timezone_name": "Australia/Sydney", "utc_offset": "+11:00"},
]


# ── Seed Functions ───────────────────────────────────────────────

async def seed_roles(db: AsyncSession) -> None:
    """Seed roles table."""
    for role_name in ROLES:
        existing = await db.execute(
            select(Role).where(Role.role_name == role_name)
        )
        if existing.scalar_one_or_none() is None:
            db.add(Role(role_name=role_name))
            print(f"  ✅ Role: {role_name}")
        else:
            print(f"  ⏭️  Role: {role_name} (exists)")


async def seed_departments(db: AsyncSession) -> None:
    """Seed departments table."""
    for dept in DEPARTMENTS:
        existing = await db.execute(
            select(Department).where(Department.name == dept["name"])
        )
        if existing.scalar_one_or_none() is None:
            db.add(Department(**dept))
            print(f"  ✅ Department: {dept['name']}")
        else:
            print(f"  ⏭️  Department: {dept['name']} (exists)")


async def seed_task_types(db: AsyncSession) -> None:
    """Seed task_types table."""
    for tt in TASK_TYPES:
        existing = await db.execute(
            select(TaskType).where(TaskType.name == tt["name"])
        )
        if existing.scalar_one_or_none() is None:
            db.add(TaskType(**tt))
            print(f"  ✅ Task Type: {tt['name']}")
        else:
            print(f"  ⏭️  Task Type: {tt['name']} (exists)")


async def seed_work_schedules(db: AsyncSession) -> None:
    """Seed work_schedules table."""
    from datetime import time as time_type

    for ws in WORK_SCHEDULES:
        existing = await db.execute(
            select(WorkSchedule).where(
                WorkSchedule.schedule_name == ws["schedule_name"]
            )
        )
        if existing.scalar_one_or_none() is None:
            h1, m1 = map(int, ws["start_time"].split(":"))
            h2, m2 = map(int, ws["end_time"].split(":"))
            db.add(WorkSchedule(
                schedule_name=ws["schedule_name"],
                start_time=time_type(h1, m1),
                end_time=time_type(h2, m2),
                break_minutes=ws["break_minutes"],
            ))
            print(f"  ✅ Work Schedule: {ws['schedule_name']}")
        else:
            print(f"  ⏭️  Work Schedule: {ws['schedule_name']} (exists)")


async def seed_time_zones(db: AsyncSession) -> None:
    """Seed time_zones table."""
    for tz in TIME_ZONES:
        existing = await db.execute(
            select(TimeZone).where(TimeZone.timezone_name == tz["timezone_name"])
        )
        if existing.scalar_one_or_none() is None:
            db.add(TimeZone(**tz))
            print(f"  ✅ TimeZone: {tz['timezone_name']}")
        else:
            print(f"  ⏭️  TimeZone: {tz['timezone_name']} (exists)")


async def run_seeds() -> None:
    """Execute all seed functions."""
    print("\n🌱 TRACE Database Seeding\n" + "=" * 40)

    async with async_session_factory() as db:
        try:
            print("\n📋 Roles:")
            await seed_roles(db)

            print("\n🏢 Departments:")
            await seed_departments(db)

            print("\n📝 Task Types:")
            await seed_task_types(db)

            print("\n⏰ Work Schedules:")
            await seed_work_schedules(db)

            print("\n🌍 Time Zones:")
            await seed_time_zones(db)

            await db.commit()
            print("\n" + "=" * 40)
            print("✅ All seeds completed successfully!\n")
        except Exception as e:
            await db.rollback()
            print(f"\n❌ Seeding failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(run_seeds())
