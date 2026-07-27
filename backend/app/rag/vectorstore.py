import logging
import uuid
from typing import Any

from app.core.config import settings
from app.embeddings.base import EmbeddingProvider

logger = logging.getLogger(__name__)


class DocumentChunk:
    def __init__(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
        doc_id: str = "",
        chunk_index: int = 0,
    ) -> None:
        self.text = text
        self.metadata = metadata or {}
        self.doc_id = doc_id
        self.chunk_index = chunk_index

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "metadata": self.metadata,
            "doc_id": self.doc_id,
            "chunk_index": self.chunk_index,
        }


class ChromaVectorStore:
    """ChromaDB wrapper with per-skill collections for isolation.
    Falls back to an in-memory dict store when ChromaDB is unavailable."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        persist_directory: str = "",
        force_memory: bool = False,
    ) -> None:
        self._embedding = embedding_provider
        self._persist_dir = persist_directory or settings.chroma_persist_directory
        self._client: Any = None
        self._collections: dict[str, Any] = {}
        self._force_memory = force_memory or persist_directory == ":memory:"

    async def _lazy_init(self) -> None:
        if self._client is not None:
            return
        if self._force_memory:
            self._client = "memory"
            return
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self._client = chromadb.PersistentClient(
                path=self._persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            logger.info("ChromaDB initialized at %s", self._persist_dir)
        except Exception:
            logger.warning("chromadb not available, using in-memory dict store")
            self._client = "memory"

    def _collection_name(self, skill_name: str | None) -> str:
        prefix = settings.vectorstore_collection_prefix
        if skill_name:
            return f"{prefix}{skill_name}"
        return f"{prefix}global"

    async def _get_collection(self, skill_name: str | None = None) -> Any:
        name = self._collection_name(skill_name)
        if name in self._collections:
            return self._collections[name]

        await self._lazy_init()
        if self._client == "memory":
            coll: dict = {}
            self._collections[name] = coll
            return coll

        try:
            collection = self._client.get_or_create_collection(
                name=name,
                metadata={"skill": skill_name or "global"},
            )
            self._collections[name] = collection
            return collection
        except Exception as exc:
            logger.error("Failed to get collection '%s': %s", name, exc)
            coll_mem: dict = {}
            self._collections[name] = coll_mem
            return coll_mem

    async def add_document(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
        skill_name: str | None = None,
        doc_id: str | None = None,
    ) -> str:
        did = doc_id or str(uuid.uuid4())
        embedding = await self._embedding.embed(text)
        collection = await self._get_collection(skill_name)

        if isinstance(collection, dict):
            collection[did] = {"text": text, "embedding": embedding, "metadata": metadata or {}}
            return did

        collection.add(
            ids=[did],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata or {}],
        )
        return did

    async def add_documents(
        self,
        chunks: list[DocumentChunk],
        skill_name: str | None = None,
    ) -> list[str]:
        if not chunks:
            return []

        texts = [c.text for c in chunks]
        embeddings = await self._embedding.embed_many(texts)
        ids = [c.doc_id or str(uuid.uuid4()) for c in chunks]
        metadatas = [c.metadata or {} for c in chunks]

        collection = await self._get_collection(skill_name)
        if isinstance(collection, dict):
            for i, did in enumerate(ids):
                collection[did] = {"text": texts[i], "embedding": embeddings[i], "metadata": metadatas[i]}
            return ids

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )
        return ids

    async def similarity_search(
        self,
        query: str,
        top_k: int = 5,
        skill_name: str | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        query_emb = await self._embedding.embed(query)
        collection = await self._get_collection(skill_name)

        if isinstance(collection, dict):
            scored: list[tuple[float, str, dict]] = []
            for did, doc in collection.items():
                emb = doc.get("embedding", [])
                if not emb:
                    continue
                score = sum(a * b for a, b in zip(query_emb, emb, strict=False))
                scored.append((score, did, doc))
            scored.sort(key=lambda x: -x[0])
            results = []
            for score, did, doc in scored[:top_k]:
                results.append({
                    "id": did,
                    "text": doc.get("text", ""),
                    "metadata": doc.get("metadata", {}),
                    "score": score,
                })
            return results

        where = {}
        if metadata_filter:
            where.update(metadata_filter)

        try:
            raw = collection.query(
                query_embeddings=[query_emb],
                n_results=top_k,
                where=where if where else None,
            )
        except Exception as exc:
            logger.error("ChromaDB query failed: %s", exc)
            return []

        results = []
        if raw and raw.get("ids") and raw["ids"][0]:
            for i in range(len(raw["ids"][0])):
                results.append({
                    "id": raw["ids"][0][i],
                    "text": raw["documents"][0][i] if raw.get("documents") else "",
                    "metadata": raw["metadatas"][0][i] if raw.get("metadatas") else {},
                    "score": raw["distances"][0][i] if raw.get("distances") else 0.0,
                })
        return results

    async def delete_document(self, doc_id: str, skill_name: str | None = None) -> bool:
        collection = await self._get_collection(skill_name)
        if isinstance(collection, dict):
            return collection.pop(doc_id, None) is not None
        try:
            collection.delete(ids=[doc_id])
            return True
        except Exception:
            return False

    async def count(self, skill_name: str | None = None) -> int:
        collection = await self._get_collection(skill_name)
        if isinstance(collection, dict):
            return len(collection)
        return collection.count()
