import pytest

from app.embeddings.providers import MockEmbeddingProvider


class TestMockEmbeddingProvider:
    @pytest.mark.asyncio
    async def test_embed_returns_correct_dimension(self) -> None:
        provider = MockEmbeddingProvider(dimension=384)
        vec = await provider.embed("hello world")
        assert len(vec) == 384

    @pytest.mark.asyncio
    async def test_embed_returns_unit_vector(self) -> None:
        provider = MockEmbeddingProvider(dimension=384)
        vec = await provider.embed("test")
        norm = sum(x * x for x in vec) ** 0.5
        assert abs(norm - 1.0) < 0.001

    @pytest.mark.asyncio
    async def test_embed_deterministic(self) -> None:
        provider = MockEmbeddingProvider(dimension=384)
        v1 = await provider.embed("same text")
        v2 = await provider.embed("same text")
        assert v1 == v2

    @pytest.mark.asyncio
    async def test_different_text_different_vectors(self) -> None:
        provider = MockEmbeddingProvider(dimension=384)
        v1 = await provider.embed("apple")
        v2 = await provider.embed("banana")
        assert v1 != v2

    @pytest.mark.asyncio
    async def test_dimension_property(self) -> None:
        provider = MockEmbeddingProvider(dimension=128)
        assert provider.dimension == 128
        assert provider.name == "mock"

    @pytest.mark.asyncio
    async def test_embed_many(self) -> None:
        provider = MockEmbeddingProvider(dimension=384)
        vecs = await provider.embed_many(["a", "b", "c"])
        assert len(vecs) == 3
        assert all(len(v) == 384 for v in vecs)
