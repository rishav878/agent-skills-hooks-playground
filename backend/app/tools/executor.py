import asyncio
import logging
import time

from app.tools.base import ToolInput, ToolOutput

logger = logging.getLogger(__name__)


class ToolExecutor:
    def __init__(self, registry: "ToolRegistry | None" = None) -> None:
        from app.tools.registry import ToolRegistry

        self._registry = registry or ToolRegistry()

    @property
    def registry(self) -> "ToolRegistry":
        return self._registry

    async def execute(
        self, tool_name: str, input_data: ToolInput | None = None
    ) -> ToolOutput:
        if input_data is None:
            input_data = ToolInput()

        tool = self._registry.get(tool_name)
        if tool is None:
            return ToolOutput(
                success=False,
                error=f"Tool '{tool_name}' not found in registry",
            )
        if not tool.metadata.enabled:
            return ToolOutput(
                success=False,
                error=f"Tool '{tool_name}' is disabled",
            )

        timeout = tool.metadata.timeout_seconds
        start = time.monotonic()
        try:
            result = await asyncio.wait_for(
                tool.execute(input_data), timeout=timeout
            )
            result.duration_ms = (time.monotonic() - start) * 1000
            return result
        except TimeoutError:
            elapsed = (time.monotonic() - start) * 1000
            logger.warning("Tool '%s' timed out after %ds", tool_name, timeout)
            return ToolOutput(
                success=False,
                error=f"Tool '{tool_name}' timed out after {timeout}s",
                duration_ms=elapsed,
            )
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            logger.exception("Tool '%s' raised an exception", tool_name)
            return ToolOutput(
                success=False,
                error=f"Tool '{tool_name}' failed: {exc!s}",
                duration_ms=elapsed,
            )
