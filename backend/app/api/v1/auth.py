"""
TRACE - Auth API Router
Endpoints: POST /register, POST /login, POST /refresh
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_optional_current_user
from app.exceptions import InsufficientPermissionsException
from app.models.user import User
from app.schemas.auth import (
    LoginRequest, LoginResponse,
    RefreshTokenRequest, RegisterRequest, RegisterResponse, TokenResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description=(
        "Create a new user account. Self-registration always creates an Employee; "
        "only an authenticated Admin may create Admin or Manager accounts."
    ),
)
async def register(
    data: RegisterRequest,
    caller: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.role != "Employee":
        caller_roles = {ur.role.role_name for ur in (caller.user_roles if caller else []) if ur.role}
        if "Admin" not in caller_roles:
            raise InsufficientPermissionsException()
    service = AuthService(db)
    return await service.register(data)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="User login",
    description="Authenticate with email and password. Returns JWT token pair.",
)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return await service.login(data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new token pair.",
)
async def refresh_token(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return await service.refresh_token(data.refresh_token)
