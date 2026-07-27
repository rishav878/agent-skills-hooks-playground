import logging
from typing import Any

from app.database.repository import Repository
from app.embeddings.base import EmbeddingProvider
from app.rag.vectorstore import ChromaVectorStore, DocumentChunk

logger = logging.getLogger(__name__)

_SKILLS_WITH_RAG: set[str] = {"research", "code_review"}


def skill_uses_rag(skill_name: str) -> bool:
    return skill_name.lower() in _SKILLS_WITH_RAG


class RAGEngine:
    """High-level RAG pipeline: ingestion, retrieval, and skill-scoped search."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: ChromaVectorStore,
        repository: Repository | None = None,
    ) -> None:
        self._embedding = embedding_provider
        self._store = vector_store
        self._repo = repository

    @property
    def store(self) -> ChromaVectorStore:
        return self._store

    async def ingest_text(
        self,
        title: str,
        content: str,
        source: str | None = None,
        skill_name: str | None = None,
        chunk_size: int = 512,
    ) -> list[dict[str, Any]]:
        if not content.strip():
            return []

        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=50,
                separators=["\n\n", "\n", ".", " ", ""],
            )
            texts = splitter.split_text(content)
            chunks: list[DocumentChunk] = []
            for i, t in enumerate(texts):
                chunks.append(
                    DocumentChunk(
                        text=t,
                        metadata={"title": title, "chunk_index": i},
                        chunk_index=i,
                    )
                )
        except ImportError:
            chunks = self._chunk_text(content, title, chunk_size)
        doc_ids = await self._store.add_documents(chunks, skill_name=skill_name)

        results = []
        for i, c in enumerate(chunks):
            results.append({
                "doc_id": doc_ids[i] if i < len(doc_ids) else "",
                "title": title,
                "text": c.text,
                "chunk_index": c.chunk_index,
                "skill_name": skill_name,
            })

        if self._repo:
            for r in results:
                await self._repo.create_document(
                    doc_id=r["doc_id"],
                    title=title,
                    content=r["text"],
                    source=source,
                    skill_name=skill_name,
                )

        return results

    async def retrieve(
        self,
        query: str,
        skill_name: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        return await self._store.similarity_search(
            query=query,
            top_k=top_k,
            skill_name=skill_name,
        )

    async def retrieve_for_skill(
        self,
        query: str,
        skill_name: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        if not skill_uses_rag(skill_name):
            return []
        return await self.retrieve(query, skill_name=skill_name, top_k=top_k)

    async def delete_document(self, doc_id: str, skill_name: str | None = None) -> bool:
        deleted = await self._store.delete_document(doc_id, skill_name)
        if deleted and self._repo:
            await self._repo.delete_document(doc_id)
        return deleted

    async def get_document_count(self, skill_name: str | None = None) -> int:
        return await self._store.count(skill_name)

    @staticmethod
    def _chunk_text(
        text: str, title: str, chunk_size: int = 512
    ) -> list[DocumentChunk]:
        words = text.split()
        chunks: list[DocumentChunk] = []
        for i in range(0, len(words), chunk_size):
            chunk_words = words[i : i + chunk_size]
            chunk_text = " ".join(chunk_words)
            chunks.append(
                DocumentChunk(
                    text=chunk_text,
                    metadata={"title": title, "chunk_index": len(chunks)},
                    chunk_index=len(chunks),
                )
            )
        return chunks
