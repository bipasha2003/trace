"""
TRACE - Role-Based Access Control (RBAC)
Provides FastAPI dependencies for role-based authorization.
"""

from enum import Enum

from fastapi import Depends

from app.dependencies import get_current_user
from app.exceptions import InsufficientPermissionsException
from app.models.user import User


class RoleEnum(str, Enum):
    """Supported roles matching the roles table."""
    ADMIN = "Admin"
    MANAGER = "Manager"
    STAFF = "Staff"


def require_roles(*allowed_roles: RoleEnum):
    """
    FastAPI dependency factory that restricts access to specific roles.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_roles(RoleEnum.ADMIN))])
        async def admin_endpoint(): ...

    Or inject the user:
        @router.get("/managers")
        async def manager_endpoint(user: User = Depends(require_roles(RoleEnum.ADMIN, RoleEnum.MANAGER))):
            ...
    """
    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        user_roles = set()
        if current_user.user_roles:
            for ur in current_user.user_roles:
                if ur.role:
                    user_roles.add(ur.role.role_name)

        allowed = {r.value for r in allowed_roles}
        if not user_roles.intersection(allowed):
            raise InsufficientPermissionsException()
        return current_user

    return role_checker


# ── Convenience shortcuts ────────────────────────────────────────

require_admin = require_roles(RoleEnum.ADMIN)
require_manager_or_admin = require_roles(RoleEnum.ADMIN, RoleEnum.MANAGER)
require_any_role = require_roles(RoleEnum.ADMIN, RoleEnum.MANAGER, RoleEnum.STAFF)
