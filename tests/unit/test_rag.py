import pytest

from app.embeddings.providers import MockEmbeddingProvider
from app.rag.engine import RAGEngine
from app.rag.vectorstore import ChromaVectorStore


@pytest.fixture
def engine() -> RAGEngine:
    embedding = MockEmbeddingProvider(dimension=384)
    store = ChromaVectorStore(embedding, persist_directory=":memory:")
    return RAGEngine(embedding, store)


class TestRAGEngine:
    @pytest.mark.asyncio
    async def test_ingest_and_retrieve(self, engine: RAGEngine) -> None:
        results = await engine.ingest_text(
            "Test Doc", "This is some test content for retrieval", skill_name="research"
        )
        assert len(results) >= 1
        assert results[0]["title"] == "Test Doc"

        retrieved = await engine.retrieve("test content", skill_name="research", top_k=5)
        assert len(retrieved) >= 1

    @pytest.mark.asyncio
    async def test_retrieve_for_skill_research(self, engine: RAGEngine) -> None:
        await engine.ingest_text("Doc", "research content here", skill_name="research")
        results = await engine.retrieve_for_skill("research", "research", top_k=5)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_retrieve_for_skill_data_analysis_returns_empty(
        self, engine: RAGEngine
    ) -> None:
        await engine.ingest_text("Doc", "data content", skill_name="data_analysis")
        results = await engine.retrieve_for_skill("data", "data_analysis", top_k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_retrieve_for_skill_code_review(self, engine: RAGEngine) -> None:
        await engine.ingest_text("Style Guide", "use 2 spaces for indentation", skill_name="code_review")
        results = await engine.retrieve_for_skill("indentation", "code_review", top_k=5)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_ingest_empty_content(self, engine: RAGEngine) -> None:
        results = await engine.ingest_text("Empty", "", skill_name="research")
        assert results == []

    @pytest.mark.asyncio
    async def test_delete_document(self, engine: RAGEngine) -> None:
        results = await engine.ingest_text("To Delete", "delete me", skill_name="research")
        assert len(results) >= 1
        doc_id = results[0]["doc_id"]
        deleted = await engine.delete_document(doc_id, skill_name="research")
        assert deleted is True

    @pytest.mark.asyncio
    async def test_get_document_count(self, engine: RAGEngine) -> None:
        assert await engine.get_document_count() == 0
        await engine.ingest_text("Doc1", "content one", skill_name="research")
        await engine.ingest_text("Doc2", "content two", skill_name="research")
        count = await engine.get_document_count(skill_name="research")
        assert count >= 1
