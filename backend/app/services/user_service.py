"""
TRACE - User Service
Business logic for user CRUD operations.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundException
from app.models.user import User, UserRole
from app.schemas.user import UserListResponse, UserResponse, UserUpdate


class UserService:
    """Handles user-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_id(self, user_id: int) -> UserResponse:
        """Fetch a single user by ID with profile and roles."""
        stmt = (
            select(User)
            .where(User.id == user_id, User.deleted_at.is_(None))
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            raise NotFoundException("User")

        return self._to_response(user)

    async def list_users(self, page: int = 1, per_page: int = 20) -> UserListResponse:
        """List users with pagination."""
        offset = (page - 1) * per_page

        # Count
        count_stmt = select(func.count(User.id)).where(User.deleted_at.is_(None))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Fetch
        stmt = (
            select(User)
            .where(User.deleted_at.is_(None))
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        result = await self.db.execute(stmt)
        users = result.scalars().all()

        return UserListResponse(
            users=[self._to_response(u) for u in users],
            total=total,
            page=page,
            per_page=per_page,
        )

    async def update_user(self, user_id: int, data: UserUpdate) -> UserResponse:
        """Update user fields."""
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            raise NotFoundException("User")

        update_data = data.model_dump(exclude_unset=True)
        if update_data.get("github_username") == "":
            update_data["github_username"] = None
        for field, value in update_data.items():
            setattr(user, field, value)

        await self.db.flush()
        return await self.get_user_by_id(user_id)

    async def soft_delete_user(self, user_id: int) -> dict:
        """Soft-delete a user."""
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            raise NotFoundException("User")

        from datetime import datetime, timezone
        user.deleted_at = datetime.now(timezone.utc)
        user.status = "Inactive"
        await self.db.flush()

        return {"message": "User deleted successfully", "user_id": user_id}

    @staticmethod
    def _to_response(user: User) -> UserResponse:
        """Convert User ORM model to response schema."""
        roles = [ur.role.role_name for ur in user.user_roles] if user.user_roles else []
        return UserResponse(
            id=user.id,
            name=user.name,
            username=user.username,
            email=user.email,
            phone=user.phone,
            gender=user.gender,
            dob=user.dob,
            is_verified=user.is_verified,
            status=user.status,
            profile=user.profile,
            roles=roles,
            github_username=user.github_username,
            created_at=user.created_at,
        )
