"""
TRACE — Admin Panel API Router
Provides comprehensive dynamic CRUD operations across all database tables
for Platform Admins and System Administrators.
"""

import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.database import get_db
from app.dependencies import get_current_user
from app.models.attendance import Attendance, TimeZone
from app.models.employee import (
    Department,
    Designation,
    Employee,
    EmployeeDetail,
    RoleMenuPermission,
    WorkSchedule,
)
from app.models.hrms import Holiday, Leave
from app.models.productivity import ProductivityScore
from app.models.task import (
    ProjectGroup,
    ProjectGroupMessage,
    Task,
    TaskComment,
    TaskDetail,
    TaskTimeLog,
    TaskType,
)
from app.models.user import Profile, Role, User, UserRole

router = APIRouter()

# Map of table name string -> SQLAlchemy Model Class
MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "users": {"model": User, "display_name": "Users", "category": "Core Auth & Users"},
    "profiles": {"model": Profile, "display_name": "Profiles", "category": "Core Auth & Users"},
    "roles": {"model": Role, "display_name": "Roles", "category": "Core Auth & Users"},
    "user_roles": {"model": UserRole, "display_name": "User Roles", "category": "Core Auth & Users"},
    "employees": {"model": Employee, "display_name": "Employees", "category": "HR & Workforce"},
    "employee_details": {"model": EmployeeDetail, "display_name": "Employee Details", "category": "HR & Workforce"},
    "departments": {"model": Department, "display_name": "Departments", "category": "HR & Workforce"},
    "designations": {"model": Designation, "display_name": "Designations", "category": "HR & Workforce"},
    "work_schedules": {"model": WorkSchedule, "display_name": "Work Schedules", "category": "HR & Workforce"},
    "role_menu_permissions": {"model": RoleMenuPermission, "display_name": "Role Permissions", "category": "HR & Workforce"},
    "attendance": {"model": Attendance, "display_name": "Attendance Records", "category": "Attendance & Schedules"},
    "time_zones": {"model": TimeZone, "display_name": "Time Zones", "category": "Attendance & Schedules"},
    "leaves": {"model": Leave, "display_name": "Leave Requests", "category": "Attendance & Schedules"},
    "holidays": {"model": Holiday, "display_name": "Holidays", "category": "Attendance & Schedules"},
    "tasks": {"model": Task, "display_name": "Tasks", "category": "Tasks & Projects"},
    "task_types": {"model": TaskType, "display_name": "Task Types", "category": "Tasks & Projects"},
    "task_details": {"model": TaskDetail, "display_name": "Task Details", "category": "Tasks & Projects"},
    "task_comments": {"model": TaskComment, "display_name": "Task Comments", "category": "Tasks & Projects"},
    "task_time_logs": {"model": TaskTimeLog, "display_name": "Task Time Logs", "category": "Tasks & Projects"},
    "project_groups": {"model": ProjectGroup, "display_name": "Project Groups", "category": "Tasks & Projects"},
    "project_group_messages": {"model": ProjectGroupMessage, "display_name": "Project Group Messages", "category": "Tasks & Projects"},
    "productivity_scores": {"model": ProductivityScore, "display_name": "Productivity Scores", "category": "AI & System"},
}


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency enforcing that current user has Platform Admin or Admin role."""
    user_roles = [ur.role.role_name for ur in user.user_roles if ur.role]
    if "Platform Admin" not in user_roles and "Admin" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin or Platform Admin role required.",
        )
    return user


def serialize_value(val: Any) -> Any:
    """Convert non-serializable objects (date, datetime, time) to ISO format."""
    if isinstance(val, (datetime.datetime, datetime.date, datetime.time)):
        return val.isoformat()
    return val


def parse_field_value(col_name: str, col_type: str, raw_value: Any) -> Any:
    """Parse string input into proper Python types for model instantiation/update."""
    if raw_value is None or raw_value == "":
        return None

    type_str = str(col_type).upper()

    if col_name == "password" and isinstance(raw_value, str) and not raw_value.startswith("$2b$"):
        return hash_password(raw_value)

    if "INT" in type_str:
        return int(raw_value)
    elif "FLOAT" in type_str or "NUMERIC" in type_str or "DECIMAL" in type_str:
        return float(raw_value)
    elif "BOOL" in type_str:
        if isinstance(raw_value, bool):
            return raw_value
        return str(raw_value).lower() in ("true", "1", "t", "yes")
    elif "DATETIME" in type_str or "TIMESTAMP" in type_str:
        if isinstance(raw_value, str):
            return datetime.datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    elif "DATE" in type_str:
        if isinstance(raw_value, str):
            return datetime.date.fromisoformat(raw_value[:10])
    elif "TIME" in type_str:
        if isinstance(raw_value, str):
            return datetime.time.fromisoformat(raw_value)

    return raw_value


@router.get("/tables", summary="Get metadata for all database tables")
async def list_tables(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Return all database tables with schema metadata and total record count."""
    table_list = []

    for table_key, meta in MODEL_REGISTRY.items():
        model_cls = meta["model"]
        mapper = inspect(model_cls)

        # Get total record count
        cnt_stmt = select(func.count()).select_from(model_cls)
        try:
            res = await db.execute(cnt_stmt)
            total_records = res.scalar_one()
        except Exception:
            total_records = 0

        # Column metadata
        columns = []
        pk_name = "id"
        for col in mapper.columns:
            if col.primary_key:
                pk_name = col.name
            columns.append({
                "name": col.name,
                "type": str(col.type),
                "nullable": col.nullable,
                "primary_key": col.primary_key,
                "default": str(col.default) if col.default else None,
            })

        table_list.append({
            "name": table_key,
            "display_name": meta["display_name"],
            "category": meta["category"],
            "total_records": total_records,
            "primary_key": pk_name,
            "columns": columns,
        })

    return {"status": "success", "tables": table_list}


@router.get("/tables/{table_name}", summary="Get records for a specific table")
async def get_table_records(
    table_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("asc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Retrieve paginated records for a specified table with search and sorting."""
    if table_name not in MODEL_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Table '{table_name}' not found in Admin Registry.",
        )

    meta = MODEL_REGISTRY[table_name]
    model_cls = meta["model"]
    mapper = inspect(model_cls)

    # Columns list
    columns = []
    pk_col = None
    for col in mapper.columns:
        if col.primary_key:
            pk_col = col
        columns.append({
            "name": col.name,
            "type": str(col.type),
            "nullable": col.nullable,
            "primary_key": col.primary_key,
        })

    pk_name = pk_col.name if pk_col is not None else "id"

    # Base query
    stmt = select(model_cls)

    # Simple text search across string columns if requested
    if search and search.strip():
        search_term = f"%{search.strip()}%"
        search_filters = []
        for col in mapper.columns:
            if "VARCHAR" in str(col.type).upper() or "TEXT" in str(col.type).upper():
                search_filters.append(col.ilike(search_term))
        if search_filters:
            stmt = stmt.where(func.or_(*search_filters))

    # Count filtered
    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_res = await db.execute(count_stmt)
    total_records = count_res.scalar_one()

    # Sorting
    if sort_by and hasattr(model_cls, sort_by):
        sort_attr = getattr(model_cls, sort_by)
        stmt = stmt.order_by(sort_attr.desc() if sort_order == "desc" else sort_attr.asc())
    elif pk_col is not None:
        stmt = stmt.order_by(pk_col.desc() if sort_order == "desc" else pk_col.asc())

    # Pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    result = await db.execute(stmt)
    records_raw = result.scalars().all()

    # Serialize records
    records = []
    for item in records_raw:
        row_dict = {}
        for col in mapper.columns:
            val = getattr(item, col.name, None)
            row_dict[col.name] = serialize_value(val)
        records.append(row_dict)

    total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 1

    return {
        "status": "success",
        "table_name": table_name,
        "display_name": meta["display_name"],
        "category": meta["category"],
        "primary_key": pk_name,
        "total": total_records,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "columns": columns,
        "records": records,
    }


@router.post("/tables/{table_name}", summary="Create a new record in a table")
async def create_table_record(
    table_name: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Insert a new record into the specified table."""
    if table_name not in MODEL_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Table '{table_name}' not found in Admin Registry.",
        )

    model_cls = MODEL_REGISTRY[table_name]["model"]
    mapper = inspect(model_cls)

    kw_args = {}
    for col in mapper.columns:
        if col.name in payload and payload[col.name] is not None:
            kw_args[col.name] = parse_field_value(col.name, str(col.type), payload[col.name])

    try:
        new_instance = model_cls(**kw_args)
        db.add(new_instance)
        await db.commit()
        await db.refresh(new_instance)

        result_dict = {}
        for col in mapper.columns:
            result_dict[col.name] = serialize_value(getattr(new_instance, col.name, None))

        return {"status": "success", "message": "Record created successfully", "record": result_dict}
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create record: {str(e)}",
        )


@router.put("/tables/{table_name}/{record_id}", summary="Update a record in a table")
async def update_table_record(
    table_name: str,
    record_id: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Update an existing record in the specified table by Primary Key."""
    if table_name not in MODEL_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Table '{table_name}' not found in Admin Registry.",
        )

    model_cls = MODEL_REGISTRY[table_name]["model"]
    mapper = inspect(model_cls)

    # Find Primary Key column
    pk_col = None
    for col in mapper.columns:
        if col.primary_key:
            pk_col = col
            break

    if pk_col is None:
        raise HTTPException(status_code=400, detail="Table lacks primary key definition")

    pk_val = parse_field_value(pk_col.name, str(pk_col.type), record_id)

    stmt = select(model_cls).where(pk_col == pk_val)
    res = await db.execute(stmt)
    instance = res.scalar_one_or_none()

    if not instance:
        raise HTTPException(status_code=404, detail="Record not found")

    try:
        for col in mapper.columns:
            if col.name in payload and not col.primary_key:
                val = parse_field_value(col.name, str(col.type), payload[col.name])
                setattr(instance, col.name, val)

        await db.commit()
        await db.refresh(instance)

        result_dict = {}
        for col in mapper.columns:
            result_dict[col.name] = serialize_value(getattr(instance, col.name, None))

        return {"status": "success", "message": "Record updated successfully", "record": result_dict}
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update record: {str(e)}",
        )


@router.delete("/tables/{table_name}/{record_id}", summary="Delete a record from a table")
async def delete_table_record(
    table_name: str,
    record_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Delete a record from the specified table by Primary Key."""
    if table_name not in MODEL_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Table '{table_name}' not found in Admin Registry.",
        )

    model_cls = MODEL_REGISTRY[table_name]["model"]
    mapper = inspect(model_cls)

    pk_col = None
    for col in mapper.columns:
        if col.primary_key:
            pk_col = col
            break

    if pk_col is None:
        raise HTTPException(status_code=400, detail="Table lacks primary key definition")

    pk_val = parse_field_value(pk_col.name, str(pk_col.type), record_id)

    stmt = select(model_cls).where(pk_col == pk_val)
    res = await db.execute(stmt)
    instance = res.scalar_one_or_none()

    if not instance:
        raise HTTPException(status_code=404, detail="Record not found")

    try:
        # Check if soft delete supported
        if hasattr(instance, "deleted_at") and getattr(instance, "deleted_at") is None:
            setattr(instance, "deleted_at", datetime.datetime.now(datetime.timezone.utc))
            message = "Record soft-deleted successfully"
        else:
            await db.delete(instance)
            message = "Record permanently deleted successfully"

        await db.commit()
        return {"status": "success", "message": message}
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete record: {str(e)}",
        )
