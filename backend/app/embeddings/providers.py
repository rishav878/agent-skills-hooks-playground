import logging
from typing import Any

from app.embeddings.base import EmbeddingProvider

logger = logging.getLogger(__name__)


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic mock for testing. Returns unit vectors derived from text hash."""

    def __init__(self, dimension: int = 384) -> None:
        self._dimension = dimension

    async def embed(self, text: str) -> list[float]:
        return self._hash_to_vector(text)

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_to_vector(t) for t in texts]

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def name(self) -> str:
        return "mock"

    @staticmethod
    def _hash_to_vector(text: str) -> list[float]:
        h = hash(text)
        vec = [float((h >> (i * 4)) & 0xFF) / 255.0 for i in range(384)]
        norm = sum(x * x for x in vec) ** 0.5
        if norm == 0:
            return vec
        return [x / norm for x in vec]


class SentenceTransformerEmbedding(EmbeddingProvider):
    """Wraps sentence-transformers for local embedding."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._model: Any = None

    async def _lazy_load(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
            logger.info(
                "Loaded sentence-transformers model: %s (dim=%d)",
                self._model_name,
                self._model.get_sentence_embedding_dimension(),
            )
        except ImportError:
            logger.warning(
                "sentence-transformers not installed, falling back to mock"
            )
            self._model = None

    async def embed(self, text: str) -> list[float]:
        await self._lazy_load()
        if self._model is None:
            return await MockEmbeddingProvider().embed(text)
        vec = self._model.encode(text, show_progress_bar=False)
        return vec.tolist()

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        await self._lazy_load()
        if self._model is None:
            return await MockEmbeddingProvider().embed_many(texts)
        vecs = self._model.encode(texts, show_progress_bar=False)
        return [v.tolist() for v in vecs]

    @property
    def dimension(self) -> int:
        return self._model.get_sentence_embedding_dimension() if self._model else 384

    @property
    def name(self) -> str:
        return f"sentence-transformers:{self._model_name}"
