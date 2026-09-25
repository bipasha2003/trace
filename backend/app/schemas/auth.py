"""
TRACE - Authentication Schemas
Pydantic models for login, register, and token operations.
"""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


# ── Request Schemas ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Schema for user registration."""
    name: str = Field(..., min_length=2, max_length=150, examples=["Bipasha Bagchi"])
    username: str = Field(..., min_length=3, max_length=100, examples=["bipasha"])
    email: EmailStr = Field(..., examples=["bipasha@trace.com"])
    password: str = Field(..., min_length=8, max_length=128, examples=["SecurePass123!"])
    phone: str | None = Field(None, max_length=20, examples=["+91-9876543210"])
    gender: str | None = Field(None, max_length=20, examples=["Female"])
    # Only an Admin may create Admin or Manager accounts — enforced in the route
    role: Literal["Admin", "Manager", "Employee"] = Field(default="Employee", examples=["Employee"])


class LoginRequest(BaseModel):
    """Schema for user login."""
    email: EmailStr = Field(..., examples=["bipasha@trace.com"])
    password: str = Field(..., examples=["SecurePass123!"])


class RefreshTokenRequest(BaseModel):
    """Schema for token refresh."""
    refresh_token: str


# ── Response Schemas ─────────────────────────────────────────────

class TokenResponse(BaseModel):
    """JWT token pair response."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class AuthUserResponse(BaseModel):
    """Authenticated user info returned after login/register."""
    id: int
    name: str
    username: str
    email: str
    roles: list[str]
    is_verified: bool
    status: str

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    """Full login response with tokens and user info."""
    tokens: TokenResponse
    user: AuthUserResponse
    message: str = "Login successful"


class RegisterResponse(BaseModel):
    """Full registration response."""
    user: AuthUserResponse
    tokens: TokenResponse
    message: str = "Registration successful"
