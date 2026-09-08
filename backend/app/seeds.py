"""
TRACE - Database Seed Script
Populates initial reference data: roles, departments, task types,
work schedules, and time zones.

Usage:
    python -m app.seeds
"""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.attendance import TimeZone
from app.models.employee import Department, Employee, WorkSchedule
from app.models.task import TaskType
from app.models.user import Profile, Role, User, UserRole

logger = logging.getLogger("trace.seeds")


# ── Reference Data ───────────────────────────────────────────────

ROLES = ["Platform Admin", "Admin", "Manager", "Staff"]

DEPARTMENTS = [
    {"name": "Design", "description": "UI/UX and graphic design team"},
    {"name": "Development", "description": "Software development and engineering"},
    {"name": "QA", "description": "Quality assurance and testing"},
    {"name": "DevOps", "description": "Infrastructure and deployment operations"},
    {"name": "HR", "description": "Human resources and people operations"},
]

DESIGNATIONS = [
    {"name": "Software Engineer", "description": "Full-stack application developer"},
    {"name": "Senior Developer", "description": "Senior software engineer"},
    {"name": "Team Lead", "description": "Engineering team lead"},
    {"name": "Product Manager", "description": "Product strategy and task manager"},
    {"name": "QA Specialist", "description": "Quality assurance engineer"},
    {"name": "HR Specialist", "description": "People operations and HR manager"},
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

# Default admin user credentials
DEFAULT_ADMIN = {
    "name": "Admin User",
    "username": "admin",
    "email": "admin@trace.com",
    "password": "Admin@123",
    "phone": "+91-9876543210",
    "gender": "Other",
}


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


async def seed_admin_user(db: AsyncSession) -> None:
    """Create the default admin user with an employee record."""
    from datetime import date

    from app.core.security import hash_password

    # Check if admin already exists
    existing = await db.execute(
        select(User).where(User.email == DEFAULT_ADMIN["email"])
    )
    if existing.scalar_one_or_none() is not None:
        print(f"  ⏭️  Admin user: {DEFAULT_ADMIN['email']} (exists)")
        return

    # Get admin role
    role_result = await db.execute(
        select(Role).where(Role.role_name == "Admin")
    )
    admin_role = role_result.scalar_one_or_none()
    if admin_role is None:
        print("  ❌ Admin role not found — skipping admin user seed")
        return

    # Get a department for the employee record
    dept_result = await db.execute(
        select(Department).where(Department.name == "Development")
    )
    dept = dept_result.scalar_one_or_none()

    # Get a work schedule
    ws_result = await db.execute(
        select(WorkSchedule).where(WorkSchedule.schedule_name == "Standard (9-6)")
    )
    work_schedule = ws_result.scalar_one_or_none()

    # Create profile
    profile = Profile()
    db.add(profile)
    await db.flush()

    # Create user
    user = User(
        name=DEFAULT_ADMIN["name"],
        username=DEFAULT_ADMIN["username"],
        email=DEFAULT_ADMIN["email"],
        password=hash_password(DEFAULT_ADMIN["password"]),
        phone=DEFAULT_ADMIN["phone"],
        gender=DEFAULT_ADMIN["gender"],
        profile_id=profile.id,
        is_verified=True,
        status="Active",
    )
    db.add(user)
    await db.flush()

    # Assign admin role
    user_role = UserRole(user_id=user.id, role_id=admin_role.id)
    db.add(user_role)
    await db.flush()

    # Create employee record so attendance/tasks work
    employee = Employee(
        user_id=user.id,
        employee_code="TRACE-001",
        department_id=dept.id if dept else None,
        work_schedule_id=work_schedule.id if work_schedule else None,
        joining_date=date.today(),
        status="Active",
    )
    db.add(employee)
    await db.flush()

    print(f"  ✅ Admin user: {DEFAULT_ADMIN['email']} (password: {DEFAULT_ADMIN['password']})")
    print(f"  ✅ Employee record: TRACE-001")


async def seed_platform_admin(db: AsyncSession) -> None:
    """Create the Platform Admin user configured via environment variables."""
    from datetime import date
    from app.config import get_settings
    from app.core.security import hash_password

    settings = get_settings()

    p_email = settings.PLATFORM_ADMIN_EMAIL
    p_username = settings.PLATFORM_ADMIN_USERNAME
    p_password = settings.PLATFORM_ADMIN_PASSWORD
    p_name = settings.PLATFORM_ADMIN_NAME

    # Check if platform admin already exists
    existing = await db.execute(
        select(User).where((User.email == p_email) | (User.username == p_username))
    )
    if existing.scalar_one_or_none() is not None:
        print(f"  ⏭️  Platform Admin user: {p_email} (exists)")
        return

    # Get platform admin role
    role_result = await db.execute(
        select(Role).where(Role.role_name == "Platform Admin")
    )
    platform_role = role_result.scalar_one_or_none()
    if platform_role is None:
        role_result = await db.execute(
            select(Role).where(Role.role_name == "Admin")
        )
        platform_role = role_result.scalar_one_or_none()

    if platform_role is None:
        print("  ❌ Neither 'Platform Admin' nor 'Admin' role found — skipping platform admin user seed")
        return

    # Get department & schedule for employee record
    dept_result = await db.execute(
        select(Department).where(Department.name == "DevOps")
    )
    dept = dept_result.scalar_one_or_none()

    ws_result = await db.execute(
        select(WorkSchedule).where(WorkSchedule.schedule_name == "Standard (9-6)")
    )
    work_schedule = ws_result.scalar_one_or_none()

    # Create profile
    profile = Profile()
    db.add(profile)
    await db.flush()

    # Create user
    user = User(
        name=p_name,
        username=p_username,
        email=p_email,
        password=hash_password(p_password),
        phone="+1-800-555-0199",
        gender="Other",
        profile_id=profile.id,
        is_verified=True,
        status="Active",
    )
    db.add(user)
    await db.flush()

    # Assign role
    user_role = UserRole(user_id=user.id, role_id=platform_role.id)
    db.add(user_role)
    await db.flush()

    # Create employee record
    employee = Employee(
        user_id=user.id,
        employee_code="PLATFORM-001",
        department_id=dept.id if dept else None,
        work_schedule_id=work_schedule.id if work_schedule else None,
        joining_date=date.today(),
        status="Active",
    )
    db.add(employee)
    await db.flush()

    print(f"  ✅ Platform Admin user: {p_email} (username: {p_username})")
    print(f"  ✅ Employee record: PLATFORM-001")


async def seed_sample_tree_and_hrms(db: AsyncSession) -> None:
    """Seed initial nested task hierarchy (Project Manager -> Team Lead -> Ground Member) and Holidays."""
    from datetime import date
    from app.models.task import Task
    from app.models.hrms import Holiday, Leave

    # Seed Holiday
    h_exist = await db.execute(select(Holiday).where(Holiday.name == "New Year's Day"))
    if not h_exist.scalar_one_or_none():
        db.add(Holiday(name="New Year's Day", holiday_date=date(2026, 1, 1), description="National holiday", type="Public"))
        db.add(Holiday(name="Independence Day", holiday_date=date(2026, 8, 15), description="National holiday", type="Public"))
        print("  ✅ Holidays seeded")

    # Check root task
    t_exist = await db.execute(select(Task).where(Task.title == "TRACE Core Engine (Project 1)"))
    if not t_exist.scalar_one_or_none():
        admin_emp = (await db.execute(select(Employee).where(Employee.employee_code == "TRACE-001"))).scalar_one_or_none()
        emp_id = admin_emp.id if admin_emp else None

        # Task 1 (Project Manager Level)
        task1 = Task(
            title="TRACE Core Engine (Project 1)",
            description="Parent project for full TRACE system setup.",
            task_level_role="Project Manager",
            project_manager_id=emp_id,
            status="WIP",
            priority="Critical",
        )
        db.add(task1)
        await db.flush()

        # Task 1.1 (Team Lead Level)
        task1_1 = Task(
            title="Authentication & Employee Tree Subsystem",
            description="Team 1 sub-project for HRMS & tree tasks.",
            parent_task_id=task1.id,
            task_level_role="Team Lead",
            team_lead_id=emp_id,
            status="WIP",
            priority="High",
        )
        db.add(task1_1)
        await db.flush()

        # Task 1.1.1 (Ground Member Level)
        task1_1_1 = Task(
            title="Ground Task: Integrate GitHub Issues API",
            description="Ground level work assigned to developer member.",
            parent_task_id=task1_1.id,
            task_level_role="Member",
            assigned_to=emp_id,
            github_issue_id="#GH-0101",
            github_issue_url="https://github.com/trace-org/trace-app/issues/101",
            status="Pending",
            priority="Medium",
        )
        db.add(task1_1_1)
        await db.flush()
        print("  ✅ Infinite Task Tree hierarchy seeded (Project Manager -> Team Lead -> Member)")


async def run_seeds() -> None:
    """Execute all seed functions."""
    print("\n🌱 TRACE Database Seeding\n" + "=" * 40)

    async with async_session_factory() as db:
        try:
            print("\n📋 Roles:")
            await seed_roles(db)

            print("\n🏢 Departments:")
            await seed_departments(db)

            print("\n💼 Designations:")
            from app.models.employee import Designation
            for desig in DESIGNATIONS:
                existing = await db.execute(select(Designation).where(Designation.name == desig["name"]))
                if existing.scalar_one_or_none() is None:
                    db.add(Designation(**desig))
                    print(f"  ✅ Designation: {desig['name']}")
                else:
                    print(f"  ⏭️  Designation: {desig['name']} (exists)")

            print("\n📝 Task Types:")
            await seed_task_types(db)

            print("\n⏰ Work Schedules:")
            await seed_work_schedules(db)

            print("\n🌍 Time Zones:")
            await seed_time_zones(db)

            print("\n👤 Admin User:")
            await seed_admin_user(db)

            print("\n👑 Platform Admin User:")
            await seed_platform_admin(db)

            print("\n🌳 Task Tree & HRMS Data:")
            await seed_sample_tree_and_hrms(db)

            await db.commit()
            print("\n" + "=" * 40)
            print("✅ All seeds completed successfully!\n")
        except Exception as e:
            await db.rollback()
            print(f"\n❌ Seeding failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(run_seeds())
