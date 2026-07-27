import ast
import asyncio
import logging
import sys
import traceback
from io import StringIO
from typing import Any

from app.tools.base import BaseTool, RiskLevel, ToolInput, ToolMetadata, ToolOutput, ToolPermission

logger = logging.getLogger(__name__)

_DENIED_BUILTINS: set[str] = {
    "__import__", "exec", "eval", "compile", "open", "input", "getattr",
}

_MAX_CODE_LENGTH = 50_000
_DENIED_DUNDER_ACCESS: set[str] = {
    "__builtins__", "__class__", "__base__", "__subclasses__",
    "__globals__", "__code__", "__closure__", "__dict__",
}

_MAX_OUTPUT_LENGTH = 100_000


def _check_code_safety(code: str) -> str | None:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return f"Syntax error: {exc!s}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in _DENIED_BUILTINS:
                return f"Use of '{func.id}' is not allowed"
            if isinstance(func, ast.Attribute):
                attr_path = _get_attribute_path(func)
                for denied in _DENIED_DUNDER_ACCESS:
                    if denied in attr_path:
                        return f"Access to '{attr_path}' is not allowed"
        if isinstance(node, ast.Attribute):
            attr_path = _get_attribute_path(node)
            for denied in _DENIED_DUNDER_ACCESS:
                if denied in attr_path:
                    return f"Access to '{attr_path}' is not allowed"
    return None


def _get_attribute_path(node: ast.Attribute) -> str:
    parts: list[str] = [node.attr]
    current = node.value
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


_RESTRICTED_GLOBALS: dict[str, Any] = {
    "__builtins__": {
        "abs": abs, "all": all, "any": any, "ascii": ascii, "bin": bin,
        "bool": bool, "bytearray": bytearray, "bytes": bytes, "chr": chr,
        "complex": complex, "dict": dict, "dir": dir, "divmod": divmod,
        "enumerate": enumerate, "filter": filter, "float": float,
        "format": format, "frozenset": frozenset,
        "hasattr": hasattr, "hash": hash, "hex": hex, "id": id,
        "int": int, "isinstance": isinstance, "issubclass": issubclass,
        "iter": iter, "len": len, "list": list, "map": map,
        "max": max, "min": min, "next": next, "object": object,
        "oct": oct, "ord": ord, "pow": pow, "print": print,
        "range": range, "repr": repr, "reversed": reversed,
        "round": round, "set": set, "slice": slice, "sorted": sorted,
        "str": str, "sum": sum, "tuple": tuple, "type": type,
        "zip": zip, "True": True, "False": False, "None": None,
    },
}


class PythonExecutionTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            ToolMetadata(
                name="python_executor",
                description="Execute Python code in a restricted sandbox",
                version="1.0.0",
                risk_level=RiskLevel.HIGH,
                permission=ToolPermission.REQUIRE_APPROVAL,
                timeout_seconds=15,
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Python code to execute"},
                    },
                    "required": ["code"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "stdout": {"type": "string"},
                        "result": {"type": "string"},
                        "error": {"type": "string"},
                    },
                },
            )
        )

    async def execute(self, input_data: ToolInput) -> ToolOutput:
        code = input_data.parameters.get("code", "")
        if not code:
            return ToolOutput(success=False, error="No Python code provided")
        if len(code) > _MAX_CODE_LENGTH:
            return ToolOutput(
                success=False,
                error=f"Code too long ({len(code)} chars, max {_MAX_CODE_LENGTH})",
            )

        safety_error = _check_code_safety(code)
        if safety_error:
            return ToolOutput(success=False, error=safety_error)

        def _run() -> tuple[str, str | None]:
            local_stdout = StringIO()
            old = sys.stdout
            sys.stdout = local_stdout
            try:
                compiled = compile(code, "<sandbox>", "exec", flags=0)
                namespace: dict[str, Any] = dict(_RESTRICTED_GLOBALS)
                exec(compiled, namespace)
                out = local_stdout.getvalue()[-_MAX_OUTPUT_LENGTH:]
                return out, None
            except Exception:
                err = traceback.format_exc()[-_MAX_OUTPUT_LENGTH:]
                out = local_stdout.getvalue()[-_MAX_OUTPUT_LENGTH:]
                return out, err
            finally:
                sys.stdout = old

        try:
            result_str, error_str = await asyncio.to_thread(_run)
        except Exception:
            error_str = traceback.format_exc()[-_MAX_OUTPUT_LENGTH:]
            result_str = ""

        return ToolOutput(
            success=error_str is None,
            result={
                "stdout": result_str,
                "error": error_str,
            },
            error=error_str,
        )
