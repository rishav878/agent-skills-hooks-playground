import logging
import os
from pathlib import Path

from app.tools.base import BaseTool, RiskLevel, ToolInput, ToolMetadata, ToolOutput, ToolPermission

logger = logging.getLogger(__name__)

_MAX_FILE_SIZE = 1_000_000


def _is_path_traversal(path: str, allowed_dir: str) -> bool:
    resolved = Path(path).resolve()
    allowed = Path(allowed_dir).resolve()
    try:
        resolved.relative_to(allowed)
        return False
    except ValueError:
        return True


class FileReaderTool(BaseTool):
    def __init__(self, allowed_directory: str | None = None) -> None:
        self._allowed_directory = (
            os.path.abspath(allowed_directory) if allowed_directory else None
        )
        super().__init__(
            ToolMetadata(
                name="file_reader",
                description="Read file contents from the allowed workspace directory",
                version="1.0.0",
                risk_level=RiskLevel.MEDIUM,
                permission=ToolPermission.REQUIRE_CONFIRM,
                timeout_seconds=10,
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path relative to workspace"},
                    },
                    "required": ["path"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string"},
                        "content": {"type": "string"},
                        "size_bytes": {"type": "integer"},
                    },
                },
            )
        )

    async def execute(self, input_data: ToolInput) -> ToolOutput:
        raw_path = input_data.parameters.get("path", "")
        if not raw_path:
            return ToolOutput(success=False, error="No file path provided")

        allowed_dir = self._allowed_directory

        try:
            p = Path(raw_path)
            target = p.resolve() if p.is_absolute() or not allowed_dir else (Path(allowed_dir) / p).resolve()
        except (OSError, RuntimeError) as exc:
            return ToolOutput(
                success=False, error=f"Invalid path: {exc!s}"
            )

        if allowed_dir:
            allowed = Path(allowed_dir).resolve()
            try:
                target.relative_to(allowed)
            except ValueError:
                return ToolOutput(
                    success=False,
                    error=f"Path '{raw_path}' is outside the allowed directory",
                )

        if not target.exists():
            return ToolOutput(
                success=False, error=f"File not found: '{raw_path}'"
            )
        if not target.is_file():
            return ToolOutput(
                success=False, error=f"Path is not a file: '{raw_path}'"
            )

        try:
            size = target.stat().st_size
            if size > _MAX_FILE_SIZE:
                return ToolOutput(
                    success=False,
                    error=f"File too large ({size} bytes, max {_MAX_FILE_SIZE})",
                )
            content = target.read_text(encoding="utf-8", errors="replace")
            return ToolOutput(
                success=True,
                result={
                    "filename": target.name,
                    "content": content,
                    "size_bytes": size,
                },
            )
        except (OSError, RuntimeError) as exc:
            return ToolOutput(
                success=False, error=f"Failed to read file: {exc!s}"
            )
