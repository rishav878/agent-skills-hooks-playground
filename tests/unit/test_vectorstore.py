import pytest

from app.embeddings.providers import MockEmbeddingProvider
from app.rag.vectorstore import ChromaVectorStore, DocumentChunk


@pytest.fixture
def store() -> ChromaVectorStore:
    embedding = MockEmbeddingProvider(dimension=384)
    return ChromaVectorStore(embedding, persist_directory=":memory:")


class TestChromaVectorStore:
    @pytest.mark.asyncio
    async def test_add_and_search(self, store: ChromaVectorStore) -> None:
        await store.add_document("hello world", skill_name="research")
        await store.add_document("goodbye world", skill_name="research")
        results = await store.similarity_search("hello", top_k=5, skill_name="research")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_add_documents_bulk(self, store: ChromaVectorStore) -> None:
        chunks = [
            DocumentChunk(text="doc one", metadata={"idx": 0}),
            DocumentChunk(text="doc two", metadata={"idx": 1}),
        ]
        ids = await store.add_documents(chunks, skill_name="code_review")
        assert len(ids) == 2

        results = await store.similarity_search(
            "doc", top_k=5, skill_name="code_review"
        )
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_empty_collection(self, store: ChromaVectorStore) -> None:
        results = await store.similarity_search("anything", top_k=5, skill_name="unknown")
        assert results == []

    @pytest.mark.asyncio
    async def test_skill_isolation(self, store: ChromaVectorStore) -> None:
        await store.add_document("research content", skill_name="research")
        await store.add_document("review content", skill_name="code_review")

        r_results = await store.similarity_search("content", top_k=5, skill_name="research")
        c_results = await store.similarity_search("content", top_k=5, skill_name="code_review")
        assert len(r_results) >= 1
        assert len(c_results) >= 1

    @pytest.mark.asyncio
    async def test_count(self, store: ChromaVectorStore) -> None:
        await store.add_document("a", skill_name="research")
        await store.add_document("b", skill_name="research")
        assert await store.count("research") == 2

    @pytest.mark.asyncio
    async def test_delete(self, store: ChromaVectorStore) -> None:
        doc_id = await store.add_document("test doc", skill_name="research")
        assert await store.count("research") == 1
        deleted = await store.delete_document(doc_id, skill_name="research")
        assert deleted is True
        assert await store.count("research") == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, store: ChromaVectorStore) -> None:
        deleted = await store.delete_document("nonexistent", skill_name="research")
        assert deleted is False
