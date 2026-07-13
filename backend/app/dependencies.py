"""
TRACE - Shared FastAPI Dependencies
Common dependencies used across all API routes.
"""

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import jwt as pyjwt

from app.config import get_settings
from app.database import get_db
from app.exceptions import InvalidTokenException, NotFoundException, TokenExpiredException
from app.models.user import User, UserRole

settings = get_settings()


async def get_current_user(
    authorization: str = Header(..., description="Bearer <token>"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract and validate the JWT from the Authorization header.
    Returns the authenticated User with roles loaded.
    """
    # Parse Bearer token
    if not authorization.startswith("Bearer "):
        raise InvalidTokenException()

    token = authorization.removeprefix("Bearer ").strip()

    try:
        payload = pyjwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except pyjwt.ExpiredSignatureError:
        raise TokenExpiredException()
    except pyjwt.InvalidTokenError:
        raise InvalidTokenException()

    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        raise InvalidTokenException()

    try:
        user_id = int(user_id_raw)
    except (ValueError, TypeError):
        raise InvalidTokenException()

    # Fetch user with roles eagerly loaded
    stmt = (
        select(User)
        .where(User.id == user_id, User.deleted_at.is_(None))
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise NotFoundException("User")

    if user.status == "Blocked":
        raise InvalidTokenException()

    return user
