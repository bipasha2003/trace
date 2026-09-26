"""
TRACE - Notifications API and the live-event socket (CORE.md §9, PROJECT.md §11.7)

Every signed-in role has notifications; each caller sees only their own.
`/ws` is the one WebSocket: it pushes "refetch" events (app.services.realtime),
never content. A browser cannot send a header on a WebSocket, so it passes its
access token as `?token=`.
"""

import jwt as pyjwt
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_any_role
from app.core.security import decode_token
from app.database import async_session_factory, get_db
from app.exceptions import NotFoundException
from app.models.project import Notification
from app.models.user import User
from app.schemas.project import NotificationList, NotificationResponse
from app.services.realtime import hub

router = APIRouter(prefix="/notifications", tags=["Notifications"], dependencies=[Depends(require_any_role)])
ws_router = APIRouter(tags=["Notifications"])


def _mine(user: User):
    return (Notification.user_id == user.id, Notification.deleted_at.is_(None))


async def _unread(db: AsyncSession, user: User) -> int:
    return (await db.execute(
        select(func.count(Notification.id)).where(*_mine(user), Notification.is_read.is_(False))
    )).scalar_one()


@router.get("", response_model=NotificationList, summary="My notifications, newest first, and the unread count")
async def list_notifications(
    unread_only: bool = False,
    limit: int = Query(30, ge=1, le=100),
    user: User = Depends(require_any_role),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Notification).where(*_mine(user))
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    items = (await db.execute(stmt.order_by(Notification.id.desc()).limit(limit))).scalars().all()
    return {"items": items, "unread": await _unread(db, user)}


@router.get("/unread-count", summary="How many of my notifications are unread")
async def unread_count(user: User = Depends(require_any_role), db: AsyncSession = Depends(get_db)):
    return {"unread": await _unread(db, user)}


@router.patch("/{notification_id}/read", response_model=NotificationResponse, summary="Mark one read")
async def mark_read(notification_id: int, user: User = Depends(require_any_role), db: AsyncSession = Depends(get_db)):
    note = (await db.execute(
        select(Notification).where(Notification.id == notification_id, *_mine(user))
    )).scalar_one_or_none()
    if note is None:
        raise NotFoundException("Notification")
    note.is_read = True
    await db.commit()
    await db.refresh(note)
    return note


@router.post("/read-all", summary="Mark all of mine read")
async def mark_all_read(user: User = Depends(require_any_role), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        update(Notification).where(*_mine(user), Notification.is_read.is_(False)).values(is_read=True)
    )
    await db.commit()
    return {"updated": result.rowcount}


@ws_router.websocket("/ws")
async def live_events(websocket: WebSocket, token: str = ""):
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise pyjwt.InvalidTokenError("not an access token")
        user_id = int(payload["sub"])
    except (pyjwt.PyJWTError, KeyError, TypeError, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    async with async_session_factory() as db:
        user = await db.get(User, user_id)
        if user is None or user.deleted_at is not None or user.status == "Blocked":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    await hub.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # the client only keeps the socket alive
    except WebSocketDisconnect:
        hub.disconnect(user_id, websocket)
