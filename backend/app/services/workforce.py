"""
TRACE - Admin → Workforce (PROJECT.md §5, §9.1; DEVELOPMENT.md Phase 8 step 2)

One curated record set, eight tabs, one shape. Each entity declares its fields
once; the same declaration drives the list columns, the add / edit form, the CSV
template and the bulk-upload validation — so the UI is one generic table and every
tab behaves the same way.

Rows are flat dicts keyed by field name. References are by a human key a
spreadsheet can carry — `employee_code`, a department or shift *name* — never a
database id. Bulk upload inserts row by row, each in a savepoint: a bad row is
reported with its line number and reason and never stops the good ones.
"""

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any, Awaitable, Callable

from pydantic import ValidationError
from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundException, TraceException
from app.models.attendance import Attendance
from app.models.employee import Department, Designation, Employee, WorkSchedule
from app.models.hrms import Holiday, Leave
from app.models.project import Project
from app.models.task import Task
from app.models.user import Role, User, UserRole

OPEN_TASK_STATUSES = ("Pending", "In Progress", "In Review", "Blocked", "Overdue")


# ── Field declarations ───────────────────────────────────────────

@dataclass
class F:
    name: str
    label: str
    type: str = "text"            # text · email · password · date · time · int · select
    required: bool = False
    options: list[str] = field(default_factory=list)
    create_only: bool = False     # the password — set once, changed through the owner's profile
    list: bool = True             # shown as a table column
    read_only: bool = False       # display only (the employee's name beside their code)

    def meta(self) -> dict:
        return {"name": self.name, "label": self.label, "type": self.type, "required": self.required,
                "options": self.options, "create_only": self.create_only, "list": self.list,
                "read_only": self.read_only}


def _coerce(f: F, raw: Any) -> Any:
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        return None
    value = raw.strip() if isinstance(raw, str) else raw
    try:
        if f.type == "int":
            return int(value)
        if f.type == "date":
            return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])
        if f.type == "time":
            return value if isinstance(value, time) else time.fromisoformat(str(value))
    except ValueError:
        kind = {"int": "a whole number", "date": "a date (YYYY-MM-DD)", "time": "a time (HH:MM)"}[f.type]
        raise TraceException(422, f"{f.label}: must be {kind}") from None
    if f.type == "email" and ("@" not in str(value) or str(value).startswith("@")):
        raise TraceException(422, f"{f.label}: must be an email address")
    if f.type == "select" and value not in f.options:
        raise TraceException(422, f"{f.label}: must be one of {', '.join(f.options)}")
    if f.type == "password" and len(str(value)) < 8:
        raise TraceException(422, f"{f.label}: must be at least 8 characters")
    return value


def clean(fields: list[F], data: dict, *, partial: bool) -> dict:
    """Coerce and check `data` against the declaration. Unknown keys are ignored."""
    out = {}
    for f in fields:
        if f.create_only and partial:
            continue
        if f.name not in data:
            if f.required and not partial:
                raise TraceException(422, f"{f.label}: is required")
            continue
        value = _coerce(f, data[f.name])
        if value is None and f.required:
            raise TraceException(422, f"{f.label}: is required")
        out[f.name] = value
    return out


# ── Shared lookups ───────────────────────────────────────────────

async def _by_name(db: AsyncSession, model, column, name: str | None, label: str):
    if not name:
        return None
    row = (await db.execute(select(model).where(func.lower(column) == name.lower(),
                                                model.deleted_at.is_(None)))).scalar_one_or_none()
    if row is None:
        raise TraceException(422, f"{label}: no {label.lower()} called '{name}'")
    return row


async def _employee_by_code(db: AsyncSession, code: str) -> Employee:
    emp = (await db.execute(select(Employee).where(Employee.employee_code == code,
                                                   Employee.deleted_at.is_(None)))).scalar_one_or_none()
    if emp is None:
        raise TraceException(422, f"Employee code: no employee with code '{code}'")
    return emp


async def _get(db: AsyncSession, model, row_id: int, label: str):
    row = await db.get(model, row_id)
    if row is None or row.deleted_at is not None:
        raise NotFoundException(label)
    return row


def _iso(value) -> str | None:
    return value.isoformat() if value is not None else None


# ── People: Employees and Managers (users with that platform role) ─

def _people_fields(role: str) -> list[F]:
    fields = [
        F("name", "Name", required=True),
        F("username", "Username", required=True),
        F("email", "Email", "email", required=True),
        F("password", "Password", "password", required=True, create_only=True, list=False),
        F("phone", "Phone", list=False),
    ]
    if role == "Employee":
        fields += [
            F("employee_code", "Employee code", required=True),
            F("github_username", "GitHub username", list=False),
            F("department", "Department"),
            F("designation", "Designation"),
            F("shift", "Shift", list=False),
            F("joining_date", "Joining date", "date", list=False),
        ]
    return fields + [F("status", "Status", "select", options=["Active", "Blocked"])]


async def _people(db: AsyncSession, role: str) -> list[User]:
    return list((await db.execute(
        select(User).join(UserRole, UserRole.user_id == User.id).join(Role, Role.id == UserRole.role_id)
        .where(Role.role_name == role, User.deleted_at.is_(None))
        .options(selectinload(User.employee).selectinload(Employee.department),
                 selectinload(User.employee).selectinload(Employee.designation),
                 selectinload(User.employee).selectinload(Employee.work_schedule))
        .order_by(User.name)
    )).scalars().unique())


def _person_row(user: User) -> dict:
    emp = user.employee
    return {
        "id": user.id, "name": user.name, "username": user.username, "email": user.email,
        "phone": user.phone, "status": user.status, "github_username": user.github_username,
        "employee_code": emp.employee_code if emp else None,
        "department": emp.department.name if emp and emp.department else None,
        "designation": emp.designation.name if emp and emp.designation else None,
        "shift": emp.work_schedule.schedule_name if emp and emp.work_schedule else None,
        "joining_date": _iso(emp.joining_date) if emp else None,
    }


async def _apply_employee(db: AsyncSession, user: User, data: dict) -> None:
    keys = {"employee_code", "department", "designation", "shift", "joining_date"}
    if not keys & data.keys():
        return
    emp = (await db.execute(select(Employee).where(Employee.user_id == user.id))).scalar_one_or_none()
    if emp is None:
        emp = Employee(user_id=user.id, employee_code=data.get("employee_code") or f"EMP-{user.id}")
        db.add(emp)
    if data.get("employee_code"):
        emp.employee_code = data["employee_code"]
    if "department" in data:
        dept = await _by_name(db, Department, Department.name, data["department"], "Department")
        emp.department_id = dept.id if dept else None
    if "designation" in data:
        des = await _by_name(db, Designation, Designation.name, data["designation"], "Designation")
        emp.designation_id = des.id if des else None
    if "shift" in data:
        shift = await _by_name(db, WorkSchedule, WorkSchedule.schedule_name, data["shift"], "Shift")
        emp.work_schedule_id = shift.id if shift else None
    if "joining_date" in data:
        emp.joining_date = data["joining_date"]
    if "status" in data:
        emp.status = "Active" if data["status"] == "Active" else "Blocked"


def people_entity(role: str):
    fields = _people_fields(role)

    async def list_(db):
        return [_person_row(u) for u in await _people(db, role)]

    async def create(db, data):
        from app.schemas.auth import RegisterRequest
        from app.services.auth_service import AuthService
        try:
            request = RegisterRequest(name=data["name"], username=data["username"], email=data["email"],
                                      password=data["password"], phone=data.get("phone"), role=role)
        except ValidationError as exc:
            raise TraceException(422, "; ".join(e["msg"] for e in exc.errors())) from None
        result = await AuthService(db).register(request)
        user = await db.get(User, result.user.id)
        user.github_username = data.get("github_username")
        user.status = data.get("status") or "Active"
        await _apply_employee(db, user, data)
        return user.id

    async def update(db, row_id, data):
        user = await _get(db, User, row_id, role)
        for key in ("name", "username", "email", "phone", "github_username", "status"):
            if key in data and (data[key] is not None or key in ("phone", "github_username")):
                setattr(user, key, data[key])
        if role == "Employee":
            await _apply_employee(db, user, data)

    async def delete(db, row_id):
        user = await _get(db, User, row_id, role)
        if role == "Employee" and (await db.execute(select(exists().where(
                Task.assigned_to_user_id == user.id, Task.deleted_at.is_(None),
                Task.status.in_(OPEN_TASK_STATUSES))))).scalar():
            raise TraceException(409, f"{user.name} still has open tasks — reassign them first")
        if role == "Manager" and (await db.execute(select(exists().where(
                Project.created_by_user_id == user.id, Project.deleted_at.is_(None))))).scalar():
            raise TraceException(409, f"{user.name} still owns projects")
        user.deleted_at, user.status = datetime.now(timezone.utc), "Blocked"

    return fields, list_, create, update, delete


# ── Simple tables ────────────────────────────────────────────────

def simple_entity(model, fields: list[F], label: str, order, to_row: Callable[[Any], dict],
                  build: Callable[[AsyncSession, Any, dict], Awaitable[None]] | None = None,
                  used_by=None):
    """A table whose fields map straight onto its columns (optionally via `build` for references).
    `used_by`: the Employee column pointing here — a row still in use is not deleted."""

    async def list_(db):
        rows = (await db.execute(select(model).where(model.deleted_at.is_(None)).order_by(*order))).scalars()
        return [to_row(r) for r in rows]

    async def assign(db, row, data):
        if build:
            await build(db, row, data)
        else:
            for key, value in data.items():
                setattr(row, key, value)

    async def create(db, data):
        row = model()
        await assign(db, row, data)
        db.add(row)
        await db.flush()
        return row.id

    async def update(db, row_id, data):
        await assign(db, await _get(db, model, row_id, label), data)

    async def delete(db, row_id):
        row = await _get(db, model, row_id, label)
        if used_by is not None and (await db.execute(select(exists().where(
                used_by == row.id, Employee.deleted_at.is_(None))))).scalar():
            raise TraceException(409, f"This {label.lower()} is still assigned to employees")
        await db.delete(row)

    return fields, list_, create, update, delete


def _named_row(r) -> dict:
    return {"id": r.id, "name": r.name, "description": r.description}


def _shift_row(r: WorkSchedule) -> dict:
    return {"id": r.id, "schedule_name": r.schedule_name, "start_time": r.start_time.strftime("%H:%M"),
            "end_time": r.end_time.strftime("%H:%M"), "break_minutes": r.break_minutes}


def _holiday_row(r: Holiday) -> dict:
    return {"id": r.id, "name": r.name, "holiday_date": _iso(r.holiday_date), "type": r.type,
            "description": r.description}


async def _codes(db: AsyncSession, employee_ids) -> dict[int, tuple[str, str]]:
    rows = (await db.execute(select(Employee.id, Employee.employee_code, User.name)
                             .join(User, User.id == Employee.user_id)
                             .where(Employee.id.in_(list(employee_ids) or [-1])))).all()
    return {r[0]: (r[1], r[2]) for r in rows}


LEAVE_FIELDS = [
    F("employee_code", "Employee code", required=True),
    F("employee_name", "Employee", read_only=True),
    F("leave_type", "Type", "select", required=True, options=["Casual", "Sick", "Earned", "Unpaid"]),
    F("start_date", "From", "date", required=True),
    F("end_date", "To", "date", required=True),
    F("reason", "Reason", list=False),
    F("status", "Status", "select", options=["Pending", "Approved", "Rejected"]),
]

ATTENDANCE_FIELDS = [
    F("employee_code", "Employee code", required=True),
    F("employee_name", "Employee", read_only=True),
    F("attendance_date", "Date", "date", required=True),
    F("time_in", "In", "time"),
    F("time_out", "Out", "time"),
    F("location_status", "Where", "select", options=["office", "remote"]),
    F("location", "Location", list=False),
]


async def _build_leave(db, row: Leave, data: dict) -> None:
    if data.get("employee_code"):
        row.employee_id = (await _employee_by_code(db, data["employee_code"])).id
    for key in ("leave_type", "start_date", "end_date", "reason", "status"):
        if key in data and (data[key] is not None or key == "reason"):
            setattr(row, key, data[key])
    row.status = row.status or "Pending"
    if row.start_date and row.end_date and row.end_date < row.start_date:
        raise TraceException(422, "To: is before From")


async def _build_attendance(db, row: Attendance, data: dict) -> None:
    if data.get("employee_code"):
        row.employee_id = (await _employee_by_code(db, data["employee_code"])).id
    if data.get("attendance_date"):
        row.attendance_date = data["attendance_date"]
    for key in ("time_in", "time_out"):
        if key in data:
            value = data[key]
            setattr(row, key, datetime.combine(row.attendance_date, value, tzinfo=timezone.utc) if value else None)
    for key in ("location", "location_status"):
        if key in data:
            setattr(row, key, data[key])
    if row.time_in and row.time_out:
        if row.time_out < row.time_in:
            raise TraceException(422, "Out: is before In")
        row.total_hours = Decimal(str(round((row.time_out - row.time_in).total_seconds() / 3600, 2)))
    else:
        row.total_hours = None


async def _list_with_codes(db, model, order, to_row):
    rows = list((await db.execute(select(model).where(model.deleted_at.is_(None)).order_by(*order))).scalars())
    codes = await _codes(db, {r.employee_id for r in rows})
    return [to_row(r, *codes.get(r.employee_id, ("", ""))) for r in rows]


def _leave_row(r: Leave, code: str, name: str) -> dict:
    return {"id": r.id, "employee_code": code, "employee_name": name, "leave_type": r.leave_type,
            "start_date": _iso(r.start_date), "end_date": _iso(r.end_date), "reason": r.reason,
            "status": r.status}


def _attendance_row(r: Attendance, code: str, name: str) -> dict:
    return {"id": r.id, "employee_code": code, "employee_name": name,
            "attendance_date": _iso(r.attendance_date),
            "time_in": r.time_in.astimezone(timezone.utc).strftime("%H:%M") if r.time_in else None,
            "time_out": r.time_out.astimezone(timezone.utc).strftime("%H:%M") if r.time_out else None,
            "location_status": r.location_status, "location": r.location}


def _with_codes(entity, model, order, to_row):
    fields, _, create, update, delete = entity

    async def list_(db):
        return await _list_with_codes(db, model, order, to_row)
    return fields, list_, create, update, delete


# ── The registry ─────────────────────────────────────────────────

ENTITIES: dict[str, tuple[str, tuple]] = {
    "employees": ("Employees", people_entity("Employee")),
    "managers": ("Managers", people_entity("Manager")),
    "leaves": ("Leaves", _with_codes(
        simple_entity(Leave, LEAVE_FIELDS, "Leave", [], lambda r: r, _build_leave),
        Leave, [Leave.start_date.desc(), Leave.id.desc()], _leave_row)),
    "holidays": ("Holidays", simple_entity(
        Holiday, [F("name", "Name", required=True), F("holiday_date", "Date", "date", required=True),
                  F("type", "Type", "select", options=["Public", "Optional", "Company"]),
                  F("description", "Description")],
        "Holiday", [Holiday.holiday_date], _holiday_row)),
    "attendance": ("Attendance", _with_codes(
        simple_entity(Attendance, ATTENDANCE_FIELDS, "Attendance record", [], lambda r: r, _build_attendance),
        Attendance, [Attendance.attendance_date.desc(), Attendance.id.desc()], _attendance_row)),
    "shifts": ("Shifts", simple_entity(
        WorkSchedule, [F("schedule_name", "Name", required=True), F("start_time", "Starts", "time", required=True),
                       F("end_time", "Ends", "time", required=True), F("break_minutes", "Break (min)", "int")],
        "Shift", [WorkSchedule.start_time], _shift_row, used_by=Employee.work_schedule_id)),
    "departments": ("Departments", simple_entity(
        Department, [F("name", "Name", required=True), F("description", "Description")],
        "Department", [Department.name], _named_row, used_by=Employee.department_id)),
    "designations": ("Designations", simple_entity(
        Designation, [F("name", "Name", required=True), F("description", "Description")],
        "Designation", [Designation.name], _named_row, used_by=Employee.designation_id)),
}

def entity(name: str):
    if name not in ENTITIES:
        raise NotFoundException("Workforce tab")
    return ENTITIES[name]


def writable(fields: list[F]) -> list[F]:
    return [f for f in fields if not f.read_only]


def catalogue() -> list[dict]:
    return [{"key": key, "label": label, "fields": [f.meta() for f in spec[0]]}
            for key, (label, spec) in ENTITIES.items()]


async def list_rows(db: AsyncSession, name: str) -> list[dict]:
    return await entity(name)[1][1](db)


async def _write(db: AsyncSession, action) -> Any:
    try:
        result = await action()
        await db.flush()
        return result
    except IntegrityError as exc:
        text = str(exc.orig).lower()
        if "unique" in text or "duplicate" in text:
            raise TraceException(409, "A record with that value already exists") from None
        if "foreign key" in text:
            raise TraceException(409, "It is still referenced by other records") from None
        raise TraceException(409, "The database refused the change") from None


async def create_row(db: AsyncSession, name: str, data: dict) -> int:
    fields, _, create, _, _ = entity(name)[1]
    values = clean(writable(fields), data, partial=False)
    return await _write(db, lambda: create(db, values))


async def update_row(db: AsyncSession, name: str, row_id: int, data: dict) -> None:
    fields, _, _, update, _ = entity(name)[1]
    values = clean(writable(fields), data, partial=True)
    await _write(db, lambda: update(db, row_id, values))


async def delete_row(db: AsyncSession, name: str, row_id: int) -> None:
    await _write(db, lambda: entity(name)[1][4](db, row_id))


def template(name: str) -> str:
    fields = writable(entity(name)[1][0])
    out = io.StringIO()
    csv.writer(out).writerow([f.name for f in fields])
    return out.getvalue()


async def bulk_upload(db: AsyncSession, name: str, content: bytes) -> dict:
    """Insert every good row; report each bad one with its line number (header = line 1)."""
    entity(name)
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise TraceException(422, "The file is not UTF-8 text — save it as CSV (UTF-8)") from None
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise TraceException(422, "The file is empty")
    known = {f.name for f in writable(entity(name)[1][0])}
    unknown = [h for h in reader.fieldnames if h and h.strip() not in known]
    created, rejected = 0, []
    for line, raw in enumerate(reader, start=2):
        row = {(k or "").strip(): v for k, v in raw.items() if k}
        if not any((v or "").strip() for v in row.values()):
            continue
        try:
            async with db.begin_nested():
                await create_row(db, name, row)
            created += 1
        except TraceException as exc:
            rejected.append({"line": line, "error": exc.detail})
    await db.commit()
    return {"created": created, "rejected": rejected, "ignored_columns": unknown}
