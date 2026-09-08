"""
TRACE - Master & Role Menu Permissions Router
Endpoints for managing system master options, dynamic roles, custom menus, and menu permissions matrix.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.employee import RoleMenuPermission, SystemMenu
from app.models.user import User, Role

router = APIRouter(prefix="/master", tags=["Master"])

DEFAULT_ROLES = ["Admin", "Manager", "Team Lead", "Employee"]
DEFAULT_MENUS = [
    {"key": "dashboard", "label": "Dashboard", "icon": "LayoutDashboard"},
    {"key": "employees", "label": "Employees", "icon": "Users"},
    {"key": "tasks", "label": "Tasks & Projects", "icon": "CheckSquare"},
    {"key": "productivity", "label": "Productivity Analytics", "icon": "BarChart3"},
    {"key": "attendance", "label": "HRMS & Attendance", "icon": "Clock"},
    {"key": "master", "label": "Master Settings", "icon": "Database"},
    {"key": "files", "label": "Files & Storage", "icon": "Folder"},
    {"key": "settings", "label": "Settings", "icon": "Settings"},
]


class RoleCreate(BaseModel):
    role_name: str


class MenuCreate(BaseModel):
    key: str
    label: str
    icon: str = "LayoutDashboard"


class MenuPermissionUpdate(BaseModel):
    role_name: str
    menu_key: str
    is_allowed: bool


class BulkMenuPermissionsUpdate(BaseModel):
    permissions: list[MenuPermissionUpdate]


# ── ROLES CRUD ───────────────────────────────────────────────────

@router.get("/roles", summary="Get all available roles")
async def get_roles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all roles from database or defaults."""
    res = await db.execute(select(Role))
    db_roles = res.scalars().all()

    if not db_roles:
        # Seed default roles into database if missing
        for r_name in DEFAULT_ROLES:
            role_obj = Role(role_name=r_name)
            db.add(role_obj)
        await db.commit()
        res = await db.execute(select(Role))
        db_roles = res.scalars().all()

    return {"roles": [{"id": r.id, "role_name": r.role_name} for r in db_roles]}


@router.post("/roles", summary="Create a new system role")
async def create_role(
    body: RoleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new role in the database."""
    role_name = body.role_name.strip()
    if not role_name:
        raise HTTPException(status_code=400, detail="Role name cannot be empty")

    existing = await db.execute(select(Role).where(Role.role_name == role_name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Role '{role_name}' already exists")

    new_role = Role(role_name=role_name)
    db.add(new_role)
    await db.commit()
    await db.refresh(new_role)

    return {"id": new_role.id, "role_name": new_role.role_name, "message": f"Role '{role_name}' created"}


@router.delete("/roles/{role_id}", summary="Delete a custom role")
async def delete_role(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a custom role."""
    role = await db.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role.role_name in ["Admin", "Manager", "Employee"]:
        raise HTTPException(status_code=400, detail="Core system roles cannot be deleted")

    await db.delete(role)
    await db.commit()
    return {"message": f"Role '{role.role_name}' deleted successfully"}


# ── MENUS CRUD ───────────────────────────────────────────────────

@router.get("/menus", summary="Get all system navigation menus")
async def get_menus(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve default and custom menus."""
    res = await db.execute(select(SystemMenu))
    custom_menus = res.scalars().all()

    all_menus = list(DEFAULT_MENUS)
    for m in custom_menus:
        if not any(dm["key"] == m.key for dm in all_menus):
            all_menus.append({
                "id": m.id,
                "key": m.key,
                "label": m.label,
                "icon": m.icon or "LayoutDashboard",
                "is_custom": True,
            })

    return {"menus": all_menus}


@router.post("/menus", summary="Create a new navigation menu/module")
async def create_menu(
    body: MenuCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a new module/menu item."""
    key = body.key.strip().lower().replace(" ", "_")
    label = body.label.strip()
    if not key or not label:
        raise HTTPException(status_code=400, detail="Menu key and label are required")

    existing = await db.execute(select(SystemMenu).where(SystemMenu.key == key))
    if existing.scalar_one_or_none() or any(dm["key"] == key for dm in DEFAULT_MENUS):
        raise HTTPException(status_code=400, detail=f"Menu key '{key}' already exists")

    menu_obj = SystemMenu(key=key, label=label, icon=body.icon, is_custom=True)
    db.add(menu_obj)
    await db.commit()
    await db.refresh(menu_obj)

    return {"id": menu_obj.id, "key": menu_obj.key, "label": menu_obj.label, "message": f"Menu '{label}' created"}


@router.delete("/menus/{menu_id}", summary="Delete a custom menu")
async def delete_menu(
    menu_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a custom navigation menu."""
    menu = await db.get(SystemMenu, menu_id)
    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")

    await db.delete(menu)
    await db.commit()
    return {"message": f"Menu '{menu.label}' deleted successfully"}


# ── MENU PERMISSIONS MATRIX ───────────────────────────────────────

@router.get("/menu-permissions", summary="Get role-menu permissions matrix")
async def get_menu_permissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Build complete permission matrix for all dynamic roles and menus."""
    # Get all roles
    res_roles = await db.execute(select(Role))
    roles = res_roles.scalars().all()
    role_names = [r.role_name for r in roles] if roles else DEFAULT_ROLES

    # Get all menus
    res_menus = await db.execute(select(SystemMenu))
    custom_menus = res_menus.scalars().all()
    all_menus = list(DEFAULT_MENUS)
    for cm in custom_menus:
        if not any(dm["key"] == cm.key for dm in all_menus):
            all_menus.append({"key": cm.key, "label": cm.label, "icon": cm.icon or "LayoutDashboard"})

    # Get stored permissions
    result = await db.execute(select(RoleMenuPermission))
    records = result.scalars().all()
    perm_map = {(r.role_name, r.menu_key): r.is_allowed for r in records}

    # Build matrix
    matrix = []
    for r_name in role_names:
        role_perms = []
        for m in all_menus:
            key = m["key"]
            default_allowed = True
            if r_name == "Employee" and key in ["master", "productivity", "employees"]:
                default_allowed = False

            allowed = perm_map.get((r_name, key), default_allowed)
            role_perms.append({"menu_key": key, "menu_label": m["label"], "is_allowed": allowed})
        matrix.append({"role_name": r_name, "permissions": role_perms})

    return {"matrix": matrix}


@router.post("/menu-permissions", summary="Update role menu permissions")
async def update_menu_permissions(
    body: BulkMenuPermissionsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk update role menu permissions."""
    for item in body.permissions:
        stmt = select(RoleMenuPermission).where(
            RoleMenuPermission.role_name == item.role_name,
            RoleMenuPermission.menu_key == item.menu_key,
        )
        res = await db.execute(stmt)
        perm = res.scalar_one_or_none()
        if perm:
            perm.is_allowed = item.is_allowed
        else:
            perm = RoleMenuPermission(
                role_name=item.role_name,
                menu_key=item.menu_key,
                is_allowed=item.is_allowed,
            )
            db.add(perm)
    await db.commit()
    return {"status": "success", "message": "Menu permissions updated successfully"}


@router.get("/my-permissions", summary="Get allowed menus for current user role")
async def get_my_permissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get navigation links accessible by current user's role."""
    user_role = "Employee"
    if current_user.user_roles:
        r = current_user.user_roles[0]
        if hasattr(r, "role") and r.role:
            user_role = r.role.role_name

    res_menus = await db.execute(select(SystemMenu))
    custom_menus = res_menus.scalars().all()
    all_menus = list(DEFAULT_MENUS)
    for cm in custom_menus:
        if not any(dm["key"] == cm.key for dm in all_menus):
            all_menus.append({"key": cm.key, "label": cm.label, "icon": cm.icon or "LayoutDashboard"})

    result = await db.execute(
        select(RoleMenuPermission).where(RoleMenuPermission.role_name == user_role)
    )
    perms = {p.menu_key: p.is_allowed for p in result.scalars().all()}

    allowed_keys = []
    for m in all_menus:
        k = m["key"]
        default_allowed = True
        if user_role == "Employee" and k in ["master", "productivity", "employees"]:
            default_allowed = False
        if perms.get(k, default_allowed):
            allowed_keys.append(k)

    return {"role": user_role, "allowed_menus": allowed_keys}
