"""
TRACE - Database Seed Script
Populates initial reference data: roles, departments, designations, task types,
work schedules, time zones, users (Admin, Manager, Employees), and a demo project.

Phase-1: updated to new role set (Admin, Manager, Employee) and demo project seed.

Usage:
    python -m app.seeds
"""

import asyncio
import logging
from datetime import date, time as time_type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import async_session_factory
from app.models.attendance import TimeZone
from app.models.employee import Department, Employee, WorkSchedule, Designation
from app.models.task import TaskType
from app.models.user import Profile, Role, User, UserRole

logger = logging.getLogger("trace.seeds")


# ── Reference Data ───────────────────────────────────────────────

ROLES = ["Admin", "Manager", "Employee"]

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

# Default users to seed — one per role plus several employees
SEED_USERS = [
    {
        "name": "Admin User",
        "username": "admin",
        "email": "admin@trace.com",
        "password": "Admin@123",
        "phone": "+91-9000000001",
        "gender": "Other",
        "role": "Admin",
        "employee_code": "TRACE-ADM-001",
    },
    {
        "name": "Manager User",
        "username": "manager",
        "email": "manager@trace.com",
        "password": "Manager@123",
        "phone": "+91-9000000002",
        "gender": "Male",
        "role": "Manager",
        "employee_code": "TRACE-MGR-001",
    },
    {
        "name": "Alice Dev",
        "username": "alice",
        "email": "alice@trace.com",
        "password": "Alice@123",
        "phone": "+91-9000000003",
        "gender": "Female",
        "role": "Employee",
        "employee_code": "TRACE-EMP-001",
    },
    {
        "name": "Bob QA",
        "username": "bob",
        "email": "bob@trace.com",
        "password": "Bob@123",
        "phone": "+91-9000000004",
        "gender": "Male",
        "role": "Employee",
        "employee_code": "TRACE-EMP-002",
    },
    {
        "name": "Carol Ops",
        "username": "carol",
        "email": "carol@trace.com",
        "password": "Carol@123",
        "phone": "+91-9000000005",
        "gender": "Female",
        "role": "Employee",
        "employee_code": "TRACE-EMP-003",
    },
]


# ── Seed Functions ───────────────────────────────────────────────

async def seed_roles(db: AsyncSession) -> None:
    """Seed roles table with the three hardcoded platform roles."""
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


async def seed_designations(db: AsyncSession) -> None:
    """Seed designations table."""
    for desig in DESIGNATIONS:
        existing = await db.execute(
            select(Designation).where(Designation.name == desig["name"])
        )
        if existing.scalar_one_or_none() is None:
            db.add(Designation(**desig))
            print(f"  ✅ Designation: {desig['name']}")
        else:
            print(f"  ⏭️  Designation: {desig['name']} (exists)")


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


async def seed_users(db: AsyncSession) -> None:
    """Create the seed users: Admin, Manager, and Employees."""
    from app.core.security import hash_password

    dept_result = await db.execute(
        select(Department).where(Department.name == "Development")
    )
    dept = dept_result.scalar_one_or_none()

    ws_result = await db.execute(
        select(WorkSchedule).where(WorkSchedule.schedule_name == "Standard (9-6)")
    )
    work_schedule = ws_result.scalar_one_or_none()

    for u_data in SEED_USERS:
        existing = await db.execute(
            select(User).where(User.email == u_data["email"])
        )
        if existing.scalar_one_or_none() is not None:
            print(f"  ⏭️  User: {u_data['email']} (exists)")
            continue

        # Get role
        role_result = await db.execute(
            select(Role).where(Role.role_name == u_data["role"])
        )
        role = role_result.scalar_one_or_none()
        if role is None:
            print(f"  ❌ Role '{u_data['role']}' not found — skipping {u_data['email']}")
            continue

        profile = Profile()
        db.add(profile)
        await db.flush()

        user = User(
            name=u_data["name"],
            username=u_data["username"],
            email=u_data["email"],
            password=hash_password(u_data["password"]),
            phone=u_data["phone"],
            gender=u_data["gender"],
            profile_id=profile.id,
            is_verified=True,
            status="Active",
        )
        db.add(user)
        await db.flush()

        db.add(UserRole(user_id=user.id, role_id=role.id))
        await db.flush()

        db.add(Employee(
            user_id=user.id,
            employee_code=u_data["employee_code"],
            department_id=dept.id if dept else None,
            work_schedule_id=work_schedule.id if work_schedule else None,
            joining_date=date.today(),
            status="Active",
        ))
        await db.flush()

        print(f"  ✅ User: {u_data['email']} ({u_data['role']}) [{u_data['employee_code']}]")


async def seed_sample_hrms(db: AsyncSession) -> None:
    """Seed initial HRMS reference data (Holidays)."""
    from app.models.hrms import Holiday

    h_exist = await db.execute(select(Holiday).where(Holiday.name == "New Year's Day"))
    if not h_exist.scalar_one_or_none():
        db.add(Holiday(name="New Year's Day", holiday_date=date(2026, 1, 1), description="National holiday", type="Public"))
        db.add(Holiday(name="Independence Day", holiday_date=date(2026, 8, 15), description="National holiday", type="Public"))
        print("  ✅ Holidays seeded")
    else:
        print("  ⏭️  Holidays (exist)")


async def seed_demo_project(db: AsyncSession) -> None:
    """Seed a demo project under the Manager user for Phase-1 verification."""
    from app.models.project import Project, ProjectAssignment, TaskGroup
    from app.models.task import Task

    # Only create if no projects exist yet
    existing_count = (await db.execute(
        select(Project).limit(1)
    )).scalar_one_or_none()
    if existing_count is not None:
        print("  ⏭️  Demo project (exists)")
        return

    # Find manager user
    manager_result = await db.execute(
        select(User).where(User.email == "manager@trace.com")
    )
    manager = manager_result.scalar_one_or_none()

    # Find alice as employee
    alice_result = await db.execute(
        select(User).where(User.email == "alice@trace.com")
    )
    alice = alice_result.scalar_one_or_none()

    if manager is None:
        print("  ❌ Manager user not found — skipping demo project")
        return

    # Create project
    project = Project(
        name="TRACE Platform MVP",
        description="Build the core TRACE project management platform with AI-driven task planning.",
        created_by_user_id=manager.id,
        # The demo repo is created by hand in the organization (TRACE creates repos only
        # for projects made through the API)
        github_repo=f"{get_settings().GITHUB_OWNER or 'org'}/trace-platform",
        github_default_branch="main",
        status="Active",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 12, 31),
    )
    db.add(project)
    await db.flush()

    # Assign alice as Project Manager on this project
    if alice:
        db.add(ProjectAssignment(
            project_id=project.id,
            user_id=alice.id,
            project_role="Project Manager",
            assigned_by_user_id=manager.id,
        ))

    # Create task groups
    groups = [
        ("Backend Foundation", "Database schema, API routes, authentication", 1, date(2026, 9, 1), date(2026, 10, 15)),
        ("Frontend Shell", "Panel layouts, routing, landing page", 2, date(2026, 9, 15), date(2026, 10, 31)),
        ("AI Pipeline", "Evaluate project, Gantt generation, task docs", 3, date(2026, 11, 1), date(2026, 12, 20)),
    ]

    group_ids = []
    for name, desc, seq, start, end in groups:
        group = TaskGroup(
            project_id=project.id,
            name=name,
            description=desc,
            sequence=seq,
            planned_start_date=start,
            planned_end_date=end,
            estimated_duration_days=(end - start).days + 1,
            status="Pending",
            created_by="Human",
        )
        db.add(group)
        await db.flush()
        group_ids.append(group.id)

        # One placeholder task per group
        task = Task(
            title=f"{name}: initial setup",
            description=f"First task for the '{name}' group.",
            project_id=project.id,
            task_group_id=group.id,
            status="Pending",
            priority="High",
        )
        db.add(task)

    await db.flush()
    # A hand-written Gantt v1 until Phase 5 generates them (DEVELOPMENT.md Phase 4):
    # the AI pipeline depends on both the backend and the frontend groups.
    from app.services import gantt_service
    backend, frontend, ai = group_ids
    await gantt_service.snapshot(db, project, "initial", dependencies=[(backend, ai), (frontend, ai)])
    print(f"  ✅ Demo project: '{project.name}' (id={project.id})")


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
            await seed_designations(db)

            print("\n📝 Task Types:")
            await seed_task_types(db)

            print("\n⏰ Work Schedules:")
            await seed_work_schedules(db)

            print("\n🌍 Time Zones:")
            await seed_time_zones(db)

            print("\n🌿 HRMS Reference Data:")
            await seed_sample_hrms(db)

            # Demo accounts have published passwords — never on a public deployment
            demo_data = not get_settings().is_production
            if demo_data:
                print("\n👥 Users (Admin · Manager · Employees):")
                await seed_users(db)

                print("\n📁 Demo Project:")
                await seed_demo_project(db)

            await db.commit()
            print("\n" + "=" * 40)
            print("✅ All seeds completed successfully!\n")
            if not demo_data:
                print("Production: demo users and demo project were not seeded.")
                return
            print("Default credentials:")
            print("  Admin:   admin@trace.com   / Admin@123")
            print("  Manager: manager@trace.com / Manager@123")
            print("  Employee: alice@trace.com  / Alice@123")
        except Exception as e:
            await db.rollback()
            print(f"\n❌ Seeding failed: {e}")
            raise


async def accounts_with_seed_passwords(db: AsyncSession) -> list[str]:
    """Emails of seeded accounts that still accept their published seed password."""
    from app.core.security import verify_password

    weak = []
    for u_data in SEED_USERS:
        user = (await db.execute(
            select(User).where(User.email == u_data["email"], User.deleted_at.is_(None))
        )).scalar_one_or_none()
        if user is not None and verify_password(u_data["password"], user.password):
            weak.append(u_data["email"])
    return weak


if __name__ == "__main__":
    asyncio.run(run_seeds())
