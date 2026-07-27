from fastapi import APIRouter

from app.api.agents import router as agents_router
from app.api.approvals import router as approvals_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.hooks import router as hooks_router
from app.api.memory_api import router as memory_router
from app.api.runs import router as runs_router
from app.api.skills import router as skills_router
from app.api.tools import router as tools_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router)
api_router.include_router(skills_router)
api_router.include_router(hooks_router)
api_router.include_router(tools_router)
api_router.include_router(agents_router)
api_router.include_router(runs_router)
api_router.include_router(approvals_router)
api_router.include_router(documents_router)
api_router.include_router(memory_router)
