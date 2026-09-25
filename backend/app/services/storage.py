"""
TRACE - Object storage for project source files (MinIO)

Source files live in MinIO; only generated markdown lives in GitHub
(PROJECT.md §11.2). The MinIO SDK is synchronous, so calls run in a thread.
"""

import asyncio
import io

from app.config import get_settings


class ObjectStorage:
    def __init__(self):
        from minio import Minio

        s = get_settings()
        self._bucket = s.MINIO_BUCKET
        self._client = Minio(s.MINIO_ENDPOINT, access_key=s.MINIO_ACCESS_KEY,
                             secret_key=s.MINIO_SECRET_KEY, secure=s.MINIO_SECURE)
        self._bucket_checked = False

    def _ensure_bucket(self) -> None:
        if not self._bucket_checked:
            if not self._client.bucket_exists(self._bucket):
                self._client.make_bucket(self._bucket)
            self._bucket_checked = True

    def _put(self, key: str, data: bytes, content_type: str) -> None:
        self._ensure_bucket()
        self._client.put_object(self._bucket, key, io.BytesIO(data), len(data), content_type=content_type)

    def _get(self, key: str) -> bytes:
        response = self._client.get_object(self._bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(self._put, key, data, content_type)

    async def get(self, key: str) -> bytes:
        return await asyncio.to_thread(self._get, key)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._client.remove_object, self._bucket, key)


_storage: ObjectStorage | None = None


def get_storage() -> ObjectStorage:
    """FastAPI dependency; tests override it with an in-memory store."""
    global _storage
    if _storage is None:
        _storage = ObjectStorage()
    return _storage
