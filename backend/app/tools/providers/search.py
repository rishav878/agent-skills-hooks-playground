from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResponse:
    query: str
    results: list[SearchResult]
    total_results: int = 0
    provider: str = "unknown"


class SearchProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def search(
        self, query: str, max_results: int = 5, **kwargs: Any
    ) -> SearchResponse: ...


class DuckDuckGoSearchProvider(SearchProvider):
    @property
    def name(self) -> str:
        return "duckduckgo"

    async def search(
        self, query: str, max_results: int = 5, **kwargs: Any
    ) -> SearchResponse:
        try:
            from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                raw = list(ddgs.text(query, max_results=max_results))
        except ImportError:
            raw = []
        except Exception:
            raw = []

        results = [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("href", ""),
                snippet=r.get("body", ""),
            )
            for r in raw
        ]
        return SearchResponse(
            query=query,
            results=results,
            total_results=len(results),
            provider=self.name,
        )


class MockSearchProvider(SearchProvider):
    def __init__(self, results: list[SearchResult] | None = None) -> None:
        self._results = results or [
            SearchResult(
                title="Mock search result",
                url="https://example.com/mock",
                snippet="This is a simulated search result",
            )
        ]

    @property
    def name(self) -> str:
        return "mock"

    async def search(
        self, query: str, max_results: int = 5, **kwargs: Any
    ) -> SearchResponse:
        return SearchResponse(
            query=query,
            results=self._results[:max_results],
            total_results=len(self._results),
            provider=self.name,
        )
