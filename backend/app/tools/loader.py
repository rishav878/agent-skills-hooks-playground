import logging
from pathlib import Path

from app.tools.base import BaseTool
from app.tools.registry import ToolRegistry
from app.tools.tools.file_reader import FileReaderTool
from app.tools.tools.python_execution import PythonExecutionTool
from app.tools.tools.web_search import WebSearchTool

logger = logging.getLogger(__name__)

_BUILTIN_TOOLS: list[type[BaseTool]] = [
    WebSearchTool,
    PythonExecutionTool,
]

_DEFAULT_ALLOWED_DIR = str(Path(__file__).resolve().parent.parent.parent)


class ToolLoader:
    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self._registry = registry or ToolRegistry()
        self._loaded = False

    @property
    def registry(self) -> ToolRegistry:
        return self._registry

    def load_builtins(self, allowed_directory: str = "") -> list[BaseTool]:
        if self._loaded:
            return self._registry.list_all()
        for tool_cls in _BUILTIN_TOOLS:
            instance = tool_cls()
            self._registry.register(instance)
            logger.debug("Loaded tool: %s", instance.metadata.name)
        file_reader = FileReaderTool(allowed_directory=allowed_directory or _DEFAULT_ALLOWED_DIR)
        self._registry.register(file_reader)
        logger.debug(
            "Loaded tool: %s (allowed_dir=%s)",
            file_reader.metadata.name,
            allowed_directory or _DEFAULT_ALLOWED_DIR,
        )
        self._loaded = True
        return self._registry.list_all()
