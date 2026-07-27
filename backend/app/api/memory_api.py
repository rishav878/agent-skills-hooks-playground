import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repository import Repository
from app.database.session import get_session
from app.memory.service import MemoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryResponse(BaseModel):
    id: str
    run_id: str
    trace_id: str
    skill_name: str
    task: str
    summary: str | None = None
    created_at: str | None = None


class ContextResponse(BaseModel):
    skill_name: str
    context: str


def _get_service(session: AsyncSession) -> MemoryService:
    repo = Repository(session)
    return MemoryService(repo)


@router.get("/{skill_name}", response_model=list[MemoryResponse])
async def get_memories(
    skill_name: str,
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> list[MemoryResponse]:
    service = _get_service(session)
    memories = await service.get_memories_by_skill(skill_name, limit=limit)
    return [MemoryResponse(**m) for m in memories]


@router.get("/{skill_name}/context", response_model=ContextResponse)
async def get_context(
    skill_name: str,
    top_k: int = Query(3, ge=1, le=10),
    session: AsyncSession = Depends(get_session),
) -> ContextResponse:
    service = _get_service(session)
    context = await service.get_recent_context(skill_name, top_k=top_k)
    return ContextResponse(skill_name=skill_name, context=context)
