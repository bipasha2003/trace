"""
TRACE - Users API Router
Endpoints for user management.
RBAC: /me is self-service. List/get require Manager+. Delete requires Admin.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_admin, require_manager_or_admin
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserListResponse, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse, summary="Get current user")
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Any authenticated user can view their own profile."""
    service = UserService(db)
    return await service.get_user_by_id(current_user.id)


@router.get(
    "",
    response_model=UserListResponse,
    summary="List all users",
    description="Admin/Manager only.",
)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_manager_or_admin),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    return await service.list_users(page=page, per_page=per_page)


@router.get("/{user_id}", response_model=UserResponse, summary="Get user by ID")
async def get_user(
    user_id: int,
    current_user: User = Depends(require_manager_or_admin),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    return await service.get_user_by_id(user_id)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Users can update their own profile. Admin can update any user.",
)
async def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Self-service: users can only update themselves unless Admin
    if current_user.id != user_id:
        from app.exceptions import InsufficientPermissionsException

        user_roles = set()
        if current_user.user_roles:
            for ur in current_user.user_roles:
                if ur.role:
                    user_roles.add(ur.role.role_name)
        if "Admin" not in user_roles:
            raise InsufficientPermissionsException()

    service = UserService(db)
    return await service.update_user(user_id, data)


@router.delete(
    "/{user_id}",
    summary="Soft-delete user",
    description="Admin only.",
)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    return await service.soft_delete_user(user_id)
