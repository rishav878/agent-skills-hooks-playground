import logging

from app.tools.base import BaseTool, RiskLevel, ToolInput, ToolMetadata, ToolOutput, ToolPermission
from app.tools.providers.search import MockSearchProvider, SearchProvider

logger = logging.getLogger(__name__)

_SEARCH_PROVIDER: SearchProvider | None = None


def set_search_provider(provider: SearchProvider) -> None:
    global _SEARCH_PROVIDER
    _SEARCH_PROVIDER = provider


def get_search_provider() -> SearchProvider:
    global _SEARCH_PROVIDER
    if _SEARCH_PROVIDER is None:
        _SEARCH_PROVIDER = MockSearchProvider()
    return _SEARCH_PROVIDER


class WebSearchTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            ToolMetadata(
                name="web_search",
                description="Search the web for information on a given query",
                version="1.0.0",
                risk_level=RiskLevel.LOW,
                permission=ToolPermission.ALWAYS_ALLOW,
                timeout_seconds=30,
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "max_results": {"type": "integer", "description": "Max results", "default": 5},
                    },
                    "required": ["query"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "results": {"type": "array"},
                        "total_results": {"type": "integer"},
                        "provider": {"type": "string"},
                    },
                },
            )
        )

    async def execute(self, input_data: ToolInput) -> ToolOutput:
        query = input_data.parameters.get("query", "")
        max_results = int(input_data.parameters.get("max_results", 5))
        if not query:
            return ToolOutput(success=False, error="No search query provided")

        provider = get_search_provider()
        try:
            response = await provider.search(query, max_results=max_results)
            return ToolOutput(
                success=True,
                result={
                    "query": response.query,
                    "results": [
                        {"title": r.title, "url": r.url, "snippet": r.snippet}
                        for r in response.results
                    ],
                    "total_results": response.total_results,
                    "provider": response.provider,
                },
            )
        except Exception as exc:
            logger.exception("Web search failed")
            return ToolOutput(
                success=False,
                error=f"Web search failed: {exc!s}",
            )
