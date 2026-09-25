"""
TRACE - Management commands

    python -m app.cli set-password <email>

Run from backend/ (./start.sh set-password <email> does this). The password is
read from the terminal, or from TRACE_NEW_PASSWORD when stdin is not a TTY.
"""

import argparse
import asyncio
import getpass
import os
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.database import async_session_factory
from app.models.user import User

MIN_PASSWORD_LENGTH = 12


def _read_password() -> str:
    if env_password := os.environ.get("TRACE_NEW_PASSWORD"):
        return env_password
    if not sys.stdin.isatty():
        sys.exit("No TTY: pass the new password in TRACE_NEW_PASSWORD.")
    first = getpass.getpass("New password: ")
    if first != getpass.getpass("Repeat it:    "):
        sys.exit("Passwords do not match.")
    return first


async def set_password(email: str, password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    async with async_session_factory() as db:
        user = (await db.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )).scalar_one_or_none()
        if user is None:
            sys.exit(f"No active user with email {email}.")
        user.password = hash_password(password)
        await db.commit()
    print(f"Password updated for {email}.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    set_pw = commands.add_parser("set-password", help="Set a user's password")
    set_pw.add_argument("email")
    args = parser.parse_args()

    if args.command == "set-password":
        asyncio.run(set_password(args.email, _read_password()))


if __name__ == "__main__":
    main()
