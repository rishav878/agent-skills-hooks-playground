import tempfile
from pathlib import Path

import pytest

from app.tools.base import (
    BaseTool,
    RiskLevel,
    ToolInput,
    ToolMetadata,
    ToolOutput,
    ToolPermission,
)
from app.tools.executor import ToolExecutor
from app.tools.loader import ToolLoader
from app.tools.providers.search import (
    MockSearchProvider,
    SearchResult,
)
from app.tools.registry import ToolRegistry
from app.tools.tools.file_reader import FileReaderTool
from app.tools.tools.python_execution import PythonExecutionTool
from app.tools.tools.web_search import WebSearchTool


class _TestTool(BaseTool):
    def __init__(
        self,
        name: str = "test_tool",
        risk: RiskLevel = RiskLevel.LOW,
        permission: ToolPermission = ToolPermission.ALWAYS_ALLOW,
        timeout: int = 30,
        enabled: bool = True,
    ) -> None:
        super().__init__(
            ToolMetadata(
                name=name,
                description=f"Test tool {name}",
                risk_level=risk,
                permission=permission,
                timeout_seconds=timeout,
                enabled=enabled,
            )
        )
        self.executed = False

    async def execute(self, input_data: ToolInput) -> ToolOutput:
        self.executed = True
        return ToolOutput(success=True, result={"echo": input_data.parameters})


class TestRiskLevel:
    def test_values(self) -> None:
        assert RiskLevel.LOW.value == "LOW"
        assert RiskLevel.MEDIUM.value == "MEDIUM"
        assert RiskLevel.HIGH.value == "HIGH"
        assert RiskLevel.CRITICAL.value == "CRITICAL"

    def test_ordering(self) -> None:
        levels = list(RiskLevel)
        assert levels == [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]


class TestToolPermission:
    def test_values(self) -> None:
        assert ToolPermission.ALWAYS_ALLOW.value == "ALWAYS_ALLOW"
        assert ToolPermission.REQUIRE_CONFIRM.value == "REQUIRE_CONFIRM"
        assert ToolPermission.DENY.value == "DENY"
        assert ToolPermission.REQUIRE_APPROVAL.value == "REQUIRE_APPROVAL"


class TestToolMetadata:
    def test_defaults(self) -> None:
        m = ToolMetadata(name="test", description="test tool")
        assert m.version == "1.0.0"
        assert m.risk_level == RiskLevel.LOW
        assert m.permission == ToolPermission.ALWAYS_ALLOW
        assert m.timeout_seconds == 30
        assert m.enabled is True

    def test_full(self) -> None:
        m = ToolMetadata(
            name="full", description="full", version="2.0.0",
            risk_level=RiskLevel.HIGH,
            permission=ToolPermission.REQUIRE_APPROVAL,
            timeout_seconds=60, enabled=False,
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            metadata={"key": "val"},
        )
        assert m.risk_level == RiskLevel.HIGH
        assert m.timeout_seconds == 60
        assert m.enabled is False


class TestToolInput:
    def test_defaults(self) -> None:
        inp = ToolInput()
        assert inp.parameters == {}
        assert inp.context == {}

    def test_full(self) -> None:
        inp = ToolInput(parameters={"a": 1}, context={"b": 2})
        assert inp.parameters == {"a": 1}
        assert inp.context == {"b": 2}


class TestToolOutput:
    def test_success(self) -> None:
        o = ToolOutput(success=True, result="done")
        assert o.success is True
        assert o.result == "done"

    def test_error(self) -> None:
        o = ToolOutput(success=False, error="failed")
        assert o.success is False
        assert o.error == "failed"


class TestBaseTool:
    def test_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            BaseTool(None)  # type: ignore[call-arg]

    @pytest.mark.asyncio
    async def test_concrete_tool(self) -> None:
        tool = _TestTool()
        assert tool.metadata.name == "test_tool"

    @pytest.mark.asyncio
    async def test_execute(self) -> None:
        tool = _TestTool()
        result = await tool.execute(ToolInput(parameters={"x": 1}))
        assert result.success is True
        assert result.result == {"echo": {"x": 1}}


class TestToolRegistry:
    def test_register_and_get(self) -> None:
        r = ToolRegistry()
        t = _TestTool("t1")
        r.register(t)
        assert r.get("t1") is t
        assert r.get_by_name("t1") is t

    def test_get_nonexistent(self) -> None:
        r = ToolRegistry()
        assert r.get("nope") is None

    def test_list_all(self) -> None:
        r = ToolRegistry()
        r.register(_TestTool("a"))
        r.register(_TestTool("b"))
        assert len(r.list_all()) == 2

    def test_list_enabled(self) -> None:
        r = ToolRegistry()
        t1 = _TestTool("t1")
        t2 = _TestTool("t2", enabled=False)
        r.register(t1)
        r.register(t2)
        assert len(r.list_enabled()) == 1

    def test_get_by_risk(self) -> None:
        r = ToolRegistry()
        low = _TestTool("low", risk=RiskLevel.LOW)
        high = _TestTool("high", risk=RiskLevel.HIGH)
        r.register(low)
        r.register(high)
        assert len(r.get_by_risk(RiskLevel.LOW)) == 1
        assert len(r.get_by_risk(RiskLevel.HIGH)) == 1
        assert len(r.get_by_risk(RiskLevel.CRITICAL)) == 0

    def test_get_by_permission(self) -> None:
        r = ToolRegistry()
        allow = _TestTool("allow", permission=ToolPermission.ALWAYS_ALLOW)
        deny = _TestTool("deny", permission=ToolPermission.DENY)
        r.register(allow)
        r.register(deny)
        assert len(r.get_by_permission(ToolPermission.ALWAYS_ALLOW)) == 1
        assert len(r.get_by_permission(ToolPermission.DENY)) == 1

    def test_remove(self) -> None:
        r = ToolRegistry()
        t = _TestTool("t")
        r.register(t)
        assert r.remove("t") is True
        assert r.get("t") is None
        assert r.remove("t") is False

    def test_remove_updates_risk_list(self) -> None:
        r = ToolRegistry()
        t = _TestTool("t", risk=RiskLevel.HIGH)
        r.register(t)
        r.remove("t")
        assert len(r.get_by_risk(RiskLevel.HIGH)) == 0

    def test_clear(self) -> None:
        r = ToolRegistry()
        r.register(_TestTool("a"))
        r.register(_TestTool("b"))
        r.clear()
        assert r.count == 0

    def test_count(self) -> None:
        r = ToolRegistry()
        assert r.count == 0
        r.register(_TestTool("a"))
        assert r.count == 1


class TestToolExecutor:
    @pytest.mark.asyncio
    async def test_execute_existing_tool(self) -> None:
        r = ToolRegistry()
        t = _TestTool("test")
        r.register(t)
        executor = ToolExecutor(r)
        result = await executor.execute("test", ToolInput(parameters={"a": 1}))
        assert result.success is True
        assert t.executed

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self) -> None:
        executor = ToolExecutor(ToolRegistry())
        result = await executor.execute("nope")
        assert result.success is False
        assert "not found" in (result.error or "")

    @pytest.mark.asyncio
    async def test_execute_disabled_tool(self) -> None:
        r = ToolRegistry()
        t = _TestTool("disabled", enabled=False)
        r.register(t)
        executor = ToolExecutor(r)
        result = await executor.execute("disabled")
        assert result.success is False
        assert "disabled" in (result.error or "")

    @pytest.mark.asyncio
    async def test_execute_timeout(self) -> None:
        class _SlowTool(BaseTool):
            def __init__(self) -> None:
                super().__init__(
                    ToolMetadata(name="slow", description="", timeout_seconds=1)
                )

            async def execute(self, input_data: ToolInput) -> ToolOutput:
                import asyncio
                await asyncio.sleep(10)
                return ToolOutput(success=True)

        r = ToolRegistry()
        r.register(_SlowTool())
        executor = ToolExecutor(r)
        result = await executor.execute("slow")
        assert result.success is False
        assert "timed out" in (result.error or "")

    @pytest.mark.asyncio
    async def test_execute_exception(self) -> None:
        class _CrashTool(BaseTool):
            def __init__(self) -> None:
                super().__init__(
                    ToolMetadata(name="crash", description="")
                )

            async def execute(self, input_data: ToolInput) -> ToolOutput:
                raise RuntimeError("boom")

        r = ToolRegistry()
        r.register(_CrashTool())
        executor = ToolExecutor(r)
        result = await executor.execute("crash")
        assert result.success is False
        assert "boom" in (result.error or "")

    @pytest.mark.asyncio
    async def test_execute_default_input(self) -> None:
        r = ToolRegistry()
        t = _TestTool("test")
        r.register(t)
        executor = ToolExecutor(r)
        result = await executor.execute("test")
        assert result.success is True


class TestToolLoader:
    def test_load_builtins(self) -> None:
        loader = ToolLoader()
        tools = loader.load_builtins()
        names = {t.metadata.name for t in tools}
        assert names == {"web_search", "python_executor", "file_reader"}

    def test_load_twice_does_not_duplicate(self) -> None:
        loader = ToolLoader()
        loader.load_builtins()
        loader.load_builtins()
        assert loader.registry.count == 3


class TestMockSearchProvider:
    @pytest.mark.asyncio
    async def test_search_returns_results(self) -> None:
        provider = MockSearchProvider()
        response = await provider.search("hello world")
        assert response.query == "hello world"
        assert len(response.results) == 1
        assert response.provider == "mock"

    @pytest.mark.asyncio
    async def test_search_with_custom_results(self) -> None:
        results = [SearchResult(title="A", url="http://a", snippet="Snippet A")]
        provider = MockSearchProvider(results)
        response = await provider.search("test", max_results=1)
        assert len(response.results) == 1
        assert response.results[0].title == "A"


class TestWebSearchTool:
    @pytest.mark.asyncio
    async def test_search_success(self) -> None:
        from app.tools.tools.web_search import set_search_provider

        set_search_provider(MockSearchProvider())
        tool = WebSearchTool()
        result = await tool.execute(ToolInput(parameters={"query": "hello world"}))
        assert result.success is True
        assert result.result["query"] == "hello world"
        assert len(result.result["results"]) > 0

    @pytest.mark.asyncio
    async def test_no_query(self) -> None:
        tool = WebSearchTool()
        result = await tool.execute(ToolInput(parameters={}))
        assert result.success is False
        assert "No search query" in (result.error or "")

    @pytest.mark.asyncio
    async def test_default_provider(self) -> None:
        from app.tools.tools.web_search import get_search_provider

        provider = get_search_provider()
        assert provider.name == "mock"


class TestPythonExecutionTool:
    @pytest.mark.asyncio
    async def test_simple_code(self) -> None:
        tool = PythonExecutionTool()
        result = await tool.execute(ToolInput(parameters={"code": "print('hello')"}))
        assert result.success is True
        assert "hello" in result.result["stdout"]

    @pytest.mark.asyncio
    async def test_math_expression(self) -> None:
        tool = PythonExecutionTool()
        result = await tool.execute(ToolInput(parameters={"code": "print(2 + 2)"}))
        assert result.success is True
        assert "4" in result.result["stdout"]

    @pytest.mark.asyncio
    async def test_no_code(self) -> None:
        tool = PythonExecutionTool()
        result = await tool.execute(ToolInput(parameters={}))
        assert result.success is False
        assert "No Python code" in (result.error or "")

    @pytest.mark.asyncio
    async def test_syntax_error(self) -> None:
        tool = PythonExecutionTool()
        result = await tool.execute(ToolInput(parameters={"code": "def foo(}  "}))
        assert result.success is False
        assert "Syntax error" in (result.error or "")

    @pytest.mark.asyncio
    async def test_blocked_builtins(self) -> None:
        tool = PythonExecutionTool()
        for blocked in ["__import__('os')", "open('/etc/passwd')", "exec('x=1')"]:
            result = await tool.execute(ToolInput(parameters={"code": blocked}))
            assert result.success is False, f"Should block: {blocked}"
            assert "not allowed" in (result.error or ""), f"Error for {blocked}: {result.error}"

    @pytest.mark.asyncio
    async def test_runtime_error(self) -> None:
        tool = PythonExecutionTool()
        result = await tool.execute(ToolInput(parameters={"code": "1/0"}))
        assert result.success is False
        assert "ZeroDivisionError" in (result.error or "")

    @pytest.mark.asyncio
    async def test_no_dunder_access(self) -> None:
        tool = PythonExecutionTool()
        result = await tool.execute(ToolInput(parameters={"code": "''.__class__"}))
        assert result.success is False
        assert "not allowed" in (result.error or "")


class TestFileReaderTool:
    @pytest.mark.asyncio
    async def test_read_existing_file(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Hello, world!")
            f.flush()
            path = f.name

        try:
            tool = FileReaderTool()
            result = await tool.execute(ToolInput(parameters={"path": path}))
            assert result.success is True
            assert result.result["content"] == "Hello, world!"
            assert result.result["size_bytes"] == 13
        finally:
            Path(path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_no_path(self) -> None:
        tool = FileReaderTool()
        result = await tool.execute(ToolInput(parameters={}))
        assert result.success is False
        assert "No file path" in (result.error or "")

    @pytest.mark.asyncio
    async def test_file_not_found(self) -> None:
        tool = FileReaderTool()
        result = await tool.execute(ToolInput(parameters={"path": "/nonexistent/file.txt"}))
        assert result.success is False
        assert "not found" in (result.error or "")

    @pytest.mark.asyncio
    async def test_directory_not_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FileReaderTool(allowed_directory=tmpdir)
            result = await tool.execute(ToolInput(parameters={"path": str(Path(tmpdir) / ".." / ".." / "etc" / "passwd")}))
            assert result.success is False
            assert "outside" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_read_within_allowed_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.txt"
            filepath.write_text("allowed content", encoding="utf-8")
            tool = FileReaderTool(allowed_directory=tmpdir)
            result = await tool.execute(ToolInput(parameters={"path": str(filepath)}))
            assert result.success is True
            assert result.result["content"] == "allowed content"


@pytest.mark.asyncio
async def test_tool_loader_integration() -> None:
    loader = ToolLoader()
    loader.load_builtins()
    assert loader.registry.count == 3

    web = loader.registry.get("web_search")
    assert web is not None
    assert web.metadata.risk_level == RiskLevel.LOW
    assert web.metadata.permission == ToolPermission.ALWAYS_ALLOW

    py = loader.registry.get("python_executor")
    assert py is not None
    assert py.metadata.risk_level == RiskLevel.HIGH
    assert py.metadata.permission == ToolPermission.REQUIRE_APPROVAL

    fr = loader.registry.get("file_reader")
    assert fr is not None
    assert fr.metadata.risk_level == RiskLevel.MEDIUM
    assert fr.metadata.permission == ToolPermission.REQUIRE_CONFIRM
