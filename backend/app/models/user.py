"""
TRACE - User, Profile, Role, and UserRole Models
Tables: users, profiles, roles, user_roles
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import BaseModelMixin


class Profile(BaseModelMixin, Base):
    """
    profiles table — stores extended user profile information.
    One-to-One with users.
    """

    __tablename__ = "profiles"

    avatar: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    emergency_contact: Mapped[str | None] = mapped_column(String(20), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Relationships ────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="profile", uselist=False)


class User(BaseModelMixin, Base):
    """
    users table — core user entity with authentication fields.
    """

    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    profile_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("profiles.id"), nullable=True
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="Active", nullable=False
    )  # Active, Inactive, Blocked, Password Changed

    # ── Relationships ────────────────────────────────────────────
    profile: Mapped[Profile | None] = relationship(
        "Profile", back_populates="user", uselist=False, lazy="joined"
    )
    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="user", lazy="selectin"
    )
    employee: Mapped["Employee | None"] = relationship(
        "Employee", back_populates="user", uselist=False
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"


class Role(BaseModelMixin, Base):
    """
    roles table — Admin, Manager, Staff.
    """

    __tablename__ = "roles"

    role_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # ── Relationships ────────────────────────────────────────────
    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="role", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, role_name={self.role_name})>"


class UserRole(BaseModelMixin, Base):
    """
    user_roles table — many-to-many link between users and roles.
    """

    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    role_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("roles.id"), nullable=False
    )

    # ── Relationships ────────────────────────────────────────────
    user: Mapped[User] = relationship("User", back_populates="user_roles")
    role: Mapped[Role] = relationship("Role", back_populates="user_roles")

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )

    def __repr__(self) -> str:
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"


# Import needed for forward references
from app.models.employee import Employee  # noqa: E402, F401
