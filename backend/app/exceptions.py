"""
TRACE - Custom Exception Classes
Centralized exception definitions for consistent error handling.
"""

from fastapi import HTTPException, status


class TraceException(HTTPException):
    """Base exception for TRACE application."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


# ── Authentication Exceptions ────────────────────────────────────

class InvalidCredentialsException(TraceException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )


class TokenExpiredException(TraceException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        )


class InvalidTokenException(TraceException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed token.",
        )


class InsufficientPermissionsException(TraceException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )


# ── Resource Exceptions ─────────────────────────────────────────

class NotFoundException(TraceException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found.",
        )


class AlreadyExistsException(TraceException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{resource} already exists.",
        )
