import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repository import Repository
from app.database.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


class IngestRequest(BaseModel):
    title: str = Field(..., max_length=500)
    content: str = Field(..., max_length=500_000)
    source: str | None = Field(None, max_length=200)
    skill_name: str | None = Field(None, max_length=100)


class SearchRequest(BaseModel):
    query: str = Field(..., max_length=10_000)
    skill_name: str | None = Field(None, max_length=100)
    top_k: int = Field(5, ge=1, le=50)


class DocumentResponse(BaseModel):
    id: str
    title: str
    content: str
    source: str | None = None
    skill_name: str | None = None
    created_at: str | None = None


class SearchResult(BaseModel):
    id: str
    text: str
    metadata: dict[str, Any] = {}
    score: float = 0.0


def _get_rag(request: Request) -> Any:
    rag = getattr(request.app.state, "rag_engine", None)
    if rag is None:
        raise HTTPException(status_code=503, detail="RAG engine not initialized")
    return rag


@router.post("/ingest")
async def ingest_document(
    body: IngestRequest,
    request: Request,
) -> dict[str, Any]:
    rag = _get_rag(request)
    chunks = await rag.ingest_text(
        title=body.title,
        content=body.content,
        source=body.source,
        skill_name=body.skill_name,
    )
    return {"chunks": len(chunks), "documents": chunks}


@router.post("/search")
async def search_documents(
    body: SearchRequest,
    request: Request,
) -> list[SearchResult]:
    rag = _get_rag(request)
    results = await rag.retrieve(
        query=body.query,
        skill_name=body.skill_name,
        top_k=body.top_k,
    )
    return [
        SearchResult(
            id=r.get("id", ""),
            text=r.get("text", ""),
            metadata=r.get("metadata", {}),
            score=r.get("score", 0.0),
        )
        for r in results
    ]


@router.post("/search/{skill_name}")
async def search_skill_documents(
    skill_name: str,
    body: SearchRequest,
    request: Request,
) -> list[SearchResult]:
    rag = _get_rag(request)
    results = await rag.retrieve_for_skill(
        query=body.query,
        skill_name=skill_name,
        top_k=body.top_k,
    )
    return [
        SearchResult(
            id=r.get("id", ""),
            text=r.get("text", ""),
            metadata=r.get("metadata", {}),
            score=r.get("score", 0.0),
        )
        for r in results
    ]


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    request: Request,
    skill_name: str | None = Query(None),
) -> dict[str, bool]:
    rag = _get_rag(request)
    deleted = await rag.delete_document(doc_id, skill_name=skill_name)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"deleted": True}


@router.get("")
async def list_documents(
    request: Request,
    skill_name: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> list[DocumentResponse]:
    repo = Repository(session)
    docs = await repo.list_documents(skill_name=skill_name)
    return [
        DocumentResponse(
            id=d.id,
            title=d.title,
            content=d.content[:200] + "..." if len(d.content) > 200 else d.content,
            source=d.source,
            skill_name=d.skill_name,
            created_at=d.created_at.isoformat() if d.created_at else None,
        )
        for d in docs
    ]


@router.get("/count")
async def document_count(
    request: Request,
    skill_name: str | None = Query(None),
) -> dict[str, int]:
    rag = _get_rag(request)
    count = await rag.get_document_count(skill_name=skill_name)
    return {"count": count}
