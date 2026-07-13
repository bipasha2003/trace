"""
TRACE - Utility Helpers
Common helper functions used across the application.
"""

import uuid
from datetime import date


def generate_employee_code(prefix: str = "EMP") -> str:
    """Generate a unique employee code."""
    short_uuid = uuid.uuid4().hex[:6].upper()
    return f"{prefix}-{short_uuid}"


def get_current_week_start() -> date:
    """Get the Monday of the current week."""
    today = date.today()
    return today - __import__("datetime").timedelta(days=today.weekday())
