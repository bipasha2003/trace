"""
TRACE - User Schemas
Pydantic models for user-related operations.
"""

from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


# ── Profile Schemas ──────────────────────────────────────────────

class ProfileBase(BaseModel):
    avatar: str | None = None
    bio: str | None = None
    address: str | None = None
    emergency_contact: str | None = None
    linkedin_url: str | None = None


class ProfileCreate(ProfileBase):
    pass


class ProfileResponse(ProfileBase):
    id: int
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── User Schemas ─────────────────────────────────────────────────

class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    phone: str | None = None
    gender: str | None = None
    dob: date | None = None


class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=150)
    phone: str | None = None
    gender: str | None = None
    dob: date | None = None


class UserResponse(UserBase):
    id: int
    is_verified: bool
    status: str
    profile: ProfileResponse | None = None
    roles: list[str] = []
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int
    page: int
    per_page: int


# ── Role Schemas ─────────────────────────────────────────────────

class RoleResponse(BaseModel):
    id: int
    role_name: str

    model_config = {"from_attributes": True}
