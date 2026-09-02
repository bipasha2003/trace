"""
TRACE - V1 API Router Aggregator
Mounts all v1 module routers under /api/v1.
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.employees import router as employees_router
from app.api.v1.attendance import router as attendance_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.productivity import router as productivity_router
from app.api.v1.services import router as services_router
from app.api.v1.hrms import router as hrms_router

router = APIRouter(prefix="/api/v1")

router.include_router(auth_router)
router.include_router(users_router)
router.include_router(employees_router)
router.include_router(attendance_router)
router.include_router(hrms_router)
router.include_router(tasks_router)
router.include_router(productivity_router)
router.include_router(services_router)
