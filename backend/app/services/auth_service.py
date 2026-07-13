"""
TRACE - Authentication Service
Business logic for user registration, login, and token management.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.exceptions import (
    AlreadyExistsException,
    InvalidCredentialsException,
    InvalidTokenException,
)
from app.models.user import Profile, Role, User, UserRole
from app.schemas.auth import (
    AuthUserResponse,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)


class AuthService:
    """Handles authentication business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, data: RegisterRequest) -> RegisterResponse:
        """
        Register a new user:
        1. Check for duplicate email/username
        2. Hash password
        3. Create profile, user, and assign role
        4. Generate JWT tokens
        """
        # ── Check duplicates ─────────────────────────────────────
        existing = await self.db.execute(
            select(User).where(
                (User.email == data.email) | (User.username == data.username),
                User.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise AlreadyExistsException("User with this email or username")

        # ── Create profile ───────────────────────────────────────
        profile = Profile()
        self.db.add(profile)
        await self.db.flush()

        # ── Create user ──────────────────────────────────────────
        user = User(
            name=data.name,
            username=data.username,
            email=data.email,
            password=hash_password(data.password),
            phone=data.phone,
            gender=data.gender,
            profile_id=profile.id,
            is_verified=False,
            status="Active",
        )
        self.db.add(user)
        await self.db.flush()

        # ── Assign role ──────────────────────────────────────────
        role = await self.db.execute(
            select(Role).where(Role.role_name == data.role)
        )
        role_obj = role.scalar_one_or_none()
        if role_obj is None:
            # Create the role if it doesn't exist (first-time setup)
            role_obj = Role(role_name=data.role)
            self.db.add(role_obj)
            await self.db.flush()

        user_role = UserRole(user_id=user.id, role_id=role_obj.id)
        self.db.add(user_role)
        await self.db.flush()

        # ── Generate tokens ──────────────────────────────────────
        token_data = {
            "sub": user.id,
            "email": user.email,
            "roles": [data.role],
        }
        tokens = TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
        )

        user_response = AuthUserResponse(
            id=user.id,
            name=user.name,
            username=user.username,
            email=user.email,
            roles=[data.role],
            is_verified=user.is_verified,
            status=user.status,
        )

        return RegisterResponse(user=user_response, tokens=tokens)

    async def login(self, data: LoginRequest) -> LoginResponse:
        """
        Authenticate user:
        1. Find user by email
        2. Verify password with bcrypt
        3. Generate JWT token pair
        """
        # ── Find user ────────────────────────────────────────────
        stmt = (
            select(User)
            .where(User.email == data.email, User.deleted_at.is_(None))
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            raise InvalidCredentialsException()

        # ── Verify password ──────────────────────────────────────
        if not verify_password(data.password, user.password):
            raise InvalidCredentialsException()

        # ── Check status ─────────────────────────────────────────
        if user.status == "Blocked":
            raise InvalidCredentialsException()

        # ── Build role list ──────────────────────────────────────
        roles = [ur.role.role_name for ur in user.user_roles]

        # ── Generate tokens ──────────────────────────────────────
        token_data = {
            "sub": user.id,
            "email": user.email,
            "roles": roles,
        }
        tokens = TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
        )

        user_response = AuthUserResponse(
            id=user.id,
            name=user.name,
            username=user.username,
            email=user.email,
            roles=roles,
            is_verified=user.is_verified,
            status=user.status,
        )

        return LoginResponse(tokens=tokens, user=user_response)

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Validate refresh token and issue a new access token."""
        try:
            payload = decode_token(refresh_token)
        except Exception:
            raise InvalidTokenException()

        if payload.get("type") != "refresh":
            raise InvalidTokenException()

        # Verify user still exists and is active
        user = await self.db.execute(
            select(User).where(User.id == payload["sub"], User.deleted_at.is_(None))
        )
        user_obj = user.scalar_one_or_none()
        if user_obj is None or user_obj.status == "Blocked":
            raise InvalidTokenException()

        token_data = {
            "sub": payload["sub"],
            "email": payload["email"],
            "roles": payload.get("roles", []),
        }

        return TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
        )
