"""
TRACE - Middleware Configuration
CORS, request logging, global exception handlers, and rate limiting.
"""

import time
import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger("trace")


def setup_middleware(app: FastAPI) -> None:
    """Configure all application middleware."""

    # ── CORS ─────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global Exception Handler ─────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """
        Catch-all for unhandled exceptions.
        Returns a structured JSON response instead of raw 500 HTML.
        """
        logger.error(
            f"Unhandled exception on {request.method} {request.url.path}: "
            f"{exc.__class__.__name__}: {exc}",
            exc_info=True,
        )

        # Don't leak internals in production
        detail = str(exc) if settings.DEBUG else "An internal error occurred."

        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "type": exc.__class__.__name__,
                "detail": detail,
                "path": request.url.path,
            },
        )

    # ── Validation Error Handler (422 → cleaner format) ──────────
    from fastapi.exceptions import RequestValidationError

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        errors = []
        for err in exc.errors():
            field = " → ".join(str(loc) for loc in err.get("loc", []))
            errors.append({
                "field": field,
                "message": err.get("msg", ""),
                "type": err.get("type", ""),
            })
        return JSONResponse(
            status_code=422,
            content={
                "error": True,
                "detail": "Validation failed",
                "errors": errors,
            },
        )

    # ── Request Logging ──────────────────────────────────────────
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        logger.info(
            f"{request.method} {request.url.path} "
            f"→ {response.status_code} "
            f"({process_time:.3f}s)"
        )

        response.headers["X-Process-Time"] = f"{process_time:.3f}"
        response.headers["X-Request-ID"] = f"{id(request):x}"
        return response
