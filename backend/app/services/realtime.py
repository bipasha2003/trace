"""
TRACE - Live events to open browsers (DEVELOPMENT.md Phase 7 step 4)

Notifications are written by the API *and* by Celery workers, but the browsers are
connected to the API. So every writer publishes a small event on one Redis channel,
and each API process relays it to the sockets of the users it names:

    publish([user_ids], {"type": "notification"})       ← API or worker, after commit
    Redis channel "trace:events"
    hub (per API process) → WebSocket /api/v1/ws of each named user

Events carry no content — only "something changed, refetch" (`notification`, or
`discussion` with a `task_id`). The browser reloads through the normal, authorised
REST routes, so a socket can never leak what its user may not read.

Tests replace `publish` with a recorder (conftest `events_sent`): no test reaches Redis.
"""

import asyncio
import json
import logging
from collections import defaultdict

from fastapi import WebSocket

from app.config import get_settings

logger = logging.getLogger("trace.realtime")

CHANNEL = "trace:events"


def publish(user_ids, event: dict) -> None:
    """Tell these users' open browsers that something changed. Never raises."""
    ids = sorted({int(u) for u in user_ids if u})
    if not ids:
        return
    try:
        import redis
        client = redis.Redis.from_url(get_settings().REDIS_URL, socket_timeout=2)
        try:
            client.publish(CHANNEL, json.dumps({"users": ids, "event": event}))
        finally:
            client.close()
    except Exception as exc:  # a missed live event is recovered by the next page load
        logger.warning("[realtime] publish failed: %s", exc)


class Hub:
    """The sockets open on this API process, by user, fed by one Redis subscriber."""

    def __init__(self):
        self.sockets: dict[int, set[WebSocket]] = defaultdict(set)
        self._listener: asyncio.Task | None = None

    async def connect(self, user_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self.sockets[user_id].add(ws)
        if self._listener is None or self._listener.done():
            self._listener = asyncio.create_task(self._listen())

    def disconnect(self, user_id: int, ws: WebSocket) -> None:
        self.sockets[user_id].discard(ws)
        if not self.sockets[user_id]:
            del self.sockets[user_id]

    def online(self) -> int:
        return len(self.sockets)

    async def deliver(self, user_ids: list[int], event: dict) -> None:
        text = json.dumps(event)
        for uid in user_ids:
            for ws in list(self.sockets.get(uid, ())):
                try:
                    await ws.send_text(text)
                except Exception:
                    self.disconnect(uid, ws)

    async def _listen(self) -> None:
        import redis.asyncio as aioredis
        while True:
            try:
                client = aioredis.Redis.from_url(get_settings().REDIS_URL)
                async with client.pubsub() as pubsub:
                    await pubsub.subscribe(CHANNEL)
                    async for message in pubsub.listen():
                        if message.get("type") != "message":
                            continue
                        data = json.loads(message["data"])
                        await self.deliver(data.get("users", []), data.get("event", {}))
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("[realtime] subscriber dropped, retrying: %s", exc)
                await asyncio.sleep(5)


hub = Hub()
