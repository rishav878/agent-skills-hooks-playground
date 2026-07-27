import pytest

from app.hooks.base import BaseHook, HookAction, HookMetadata, HookResult, LifecycleEvent
from app.hooks.executor import HookExecutor, deep_merge
from app.hooks.hooks.human_approval import HumanApprovalHook
from app.hooks.hooks.logging_hook import LoggingHook
from app.hooks.hooks.output_validation import OutputValidationHook
from app.hooks.hooks.request_validation import RequestValidationHook
from app.hooks.hooks.security import SecurityHook
from app.hooks.hooks.tool_permission import ToolPermissionHook
from app.hooks.manager import HookManager
from app.hooks.registry import HookRegistry


class _TestHook(BaseHook):
    def __init__(
        self,
        name: str,
        lifecycle_event: LifecycleEvent,
        result: HookResult | None = None,
        priority: int = 0,
    ) -> None:
        super().__init__(
            HookMetadata(
                name=name,
                description=f"Test hook {name}",
                lifecycle_event=lifecycle_event,
                priority=priority,
            )
        )
        self._result = result or HookResult(action=HookAction.CONTINUE)
        self.executed = False

    async def execute(self, context: dict) -> HookResult:
        self.executed = True
        return self._result


class TestHookAction:
    def test_values(self) -> None:
        assert HookAction.CONTINUE.value == "CONTINUE"
        assert HookAction.BLOCK.value == "BLOCK"
        assert HookAction.MODIFY.value == "MODIFY"
        assert HookAction.RETRY.value == "RETRY"
        assert HookAction.APPROVAL_REQUIRED.value == "APPROVAL_REQUIRED"

    def test_membership(self) -> None:
        assert HookAction.CONTINUE in HookAction


class TestLifecycleEvent:
    def test_all_events_present(self) -> None:
        expected = {
            "before_request", "after_request",
            "before_agent", "after_agent",
            "before_skill", "after_skill",
            "before_tool", "after_tool",
            "before_llm", "after_llm",
            "before_response", "after_response",
        }
        actual = {e.value for e in LifecycleEvent}
        assert actual == expected

    def test_values(self) -> None:
        assert LifecycleEvent.before_request.value == "before_request"
        assert LifecycleEvent.after_tool.value == "after_tool"


class TestHookResult:
    def test_defaults(self) -> None:
        r = HookResult()
        assert r.action == HookAction.CONTINUE
        assert r.modifications == {}
        assert r.reason == ""

    def test_full(self) -> None:
        r = HookResult(
            action=HookAction.BLOCK,
            modifications={"key": "value"},
            reason="test reason",
        )
        assert r.action == HookAction.BLOCK
        assert r.modifications == {"key": "value"}
        assert r.reason == "test reason"


class TestHookMetadata:
    def test_defaults(self) -> None:
        m = HookMetadata(
            name="test", description="desc", lifecycle_event=LifecycleEvent.before_request
        )
        assert m.name == "test"
        assert m.priority == 0
        assert m.enabled is True
        assert m.metadata == {}

    def test_full(self) -> None:
        m = HookMetadata(
            name="full",
            description="full desc",
            lifecycle_event=LifecycleEvent.after_tool,
            priority=50,
            enabled=False,
            metadata={"key": "val"},
        )
        assert m.priority == 50
        assert m.enabled is False
        assert m.metadata == {"key": "val"}


class TestBaseHook:
    def test_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            BaseHook(None)  # type: ignore[call-arg]

    def test_concrete_hook(self) -> None:
        hook = _TestHook("t1", LifecycleEvent.before_request)
        assert hook.metadata.name == "t1"

    @pytest.mark.asyncio
    async def test_execute(self) -> None:
        hook = _TestHook("t1", LifecycleEvent.before_request)
        result = await hook.execute({})
        assert result.action == HookAction.CONTINUE


class TestHookRegistry:
    def test_register_and_get(self) -> None:
        registry = HookRegistry()
        hook = _TestHook("h1", LifecycleEvent.before_request)
        registry.register(hook)
        assert registry.get("h1") is hook
        assert registry.get_by_name("h1") is hook

    def test_get_nonexistent(self) -> None:
        registry = HookRegistry()
        assert registry.get("nope") is None
        assert registry.get_by_name("nope") is None

    def test_list_all(self) -> None:
        registry = HookRegistry()
        registry.register(_TestHook("a", LifecycleEvent.before_request))
        registry.register(_TestHook("b", LifecycleEvent.before_request))
        assert len(registry.list_all()) == 2

    def test_list_enabled(self) -> None:
        registry = HookRegistry()
        h1 = _TestHook("h1", LifecycleEvent.before_request)
        h2 = _TestHook("h2", LifecycleEvent.before_request)
        h2.metadata.enabled = False
        registry.register(h1)
        registry.register(h2)
        enabled = registry.list_enabled()
        assert len(enabled) == 1
        assert enabled[0] is h1

    def test_get_for_event(self) -> None:
        registry = HookRegistry()
        h1 = _TestHook("h1", LifecycleEvent.before_request)
        h2 = _TestHook("h2", LifecycleEvent.before_request)
        h3 = _TestHook("h3", LifecycleEvent.after_request)
        registry.register(h1)
        registry.register(h2)
        registry.register(h3)
        before = registry.get_for_event(LifecycleEvent.before_request)
        assert len(before) == 2
        after = registry.get_for_event(LifecycleEvent.after_request)
        assert len(after) == 1

    def test_get_for_event_disabled_excluded(self) -> None:
        registry = HookRegistry()
        h1 = _TestHook("h1", LifecycleEvent.before_request)
        h1.metadata.enabled = False
        registry.register(h1)
        assert len(registry.get_for_event(LifecycleEvent.before_request)) == 0

    def test_remove(self) -> None:
        registry = HookRegistry()
        h = _TestHook("h", LifecycleEvent.before_request)
        registry.register(h)
        assert registry.remove("h") is True
        assert registry.get("h") is None
        assert registry.remove("h") is False

    def test_remove_updates_event_list(self) -> None:
        registry = HookRegistry()
        h = _TestHook("h", LifecycleEvent.before_request)
        registry.register(h)
        registry.remove("h")
        assert len(registry.get_for_event(LifecycleEvent.before_request)) == 0

    def test_clear(self) -> None:
        registry = HookRegistry()
        registry.register(_TestHook("a", LifecycleEvent.before_request))
        registry.register(_TestHook("b", LifecycleEvent.after_request))
        registry.clear()
        assert registry.count == 0
        assert len(registry.list_all()) == 0

    def test_count(self) -> None:
        registry = HookRegistry()
        assert registry.count == 0
        registry.register(_TestHook("a", LifecycleEvent.before_request))
        assert registry.count == 1


class TestDeepMerge:
    def test_basic_override(self) -> None:
        result = deep_merge({"a": 1, "b": 2}, {"b": 3, "c": 4})
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self) -> None:
        result = deep_merge(
            {"outer": {"inner": 1, "other": 2}},
            {"outer": {"inner": 99}},
        )
        assert result == {"outer": {"inner": 99, "other": 2}}

    def test_new_key_added(self) -> None:
        result = deep_merge({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_empty_override(self) -> None:
        result = deep_merge({"a": 1}, {})
        assert result == {"a": 1}

    def test_original_not_mutated(self) -> None:
        original = {"a": [1, 2]}
        result = deep_merge(original, {"a": [3]})
        assert original["a"] == [1, 2]
        assert result["a"] == [3]


class TestHookExecutor:
    @pytest.mark.asyncio
    async def test_no_hooks_returns_continue(self) -> None:
        registry = HookRegistry()
        executor = HookExecutor(registry)
        result = await executor.run_pipeline(LifecycleEvent.before_request, {})
        assert result.action == HookAction.CONTINUE
        assert result.reason == "No hooks registered"

    @pytest.mark.asyncio
    async def test_priority_ordering(self) -> None:
        registry = HookRegistry()
        h1 = _TestHook("low", LifecycleEvent.before_request, priority=100)
        h2 = _TestHook("high", LifecycleEvent.before_request, priority=-100)
        h3 = _TestHook("mid", LifecycleEvent.before_request, priority=0)
        registry.register(h1)
        registry.register(h2)
        registry.register(h3)
        executor = HookExecutor(registry)
        await executor.run_pipeline(LifecycleEvent.before_request, {})
        order = [h.metadata.name for h in executor._get_sorted_hooks(LifecycleEvent.before_request)]
        assert order == ["high", "mid", "low"]

    @pytest.mark.asyncio
    async def test_all_continue(self) -> None:
        registry = HookRegistry()
        h1 = _TestHook("a", LifecycleEvent.before_request)
        h2 = _TestHook("b", LifecycleEvent.before_request)
        registry.register(h1)
        registry.register(h2)
        executor = HookExecutor(registry)
        result = await executor.run_pipeline(LifecycleEvent.before_request, {})
        assert result.action == HookAction.CONTINUE
        assert h1.executed
        assert h2.executed

    @pytest.mark.asyncio
    async def test_block_halts_pipeline(self) -> None:
        registry = HookRegistry()
        h1 = _TestHook("blocker", LifecycleEvent.before_request, result=HookResult(action=HookAction.BLOCK, reason="blocked"))
        h2 = _TestHook("after", LifecycleEvent.before_request)
        registry.register(h1)
        registry.register(h2)
        executor = HookExecutor(registry)
        result = await executor.run_pipeline(LifecycleEvent.before_request, {})
        assert result.action == HookAction.BLOCK
        assert "blocked" in result.reason
        assert h1.executed
        assert not h2.executed

    @pytest.mark.asyncio
    async def test_modify_accumulates(self) -> None:
        registry = HookRegistry()
        h1 = _TestHook(
            "mod1", LifecycleEvent.before_skill,
            result=HookResult(action=HookAction.MODIFY, modifications={"ctx": {"a": 1}}, reason="mod1"),
            priority=0,
        )
        h2 = _TestHook(
            "mod2", LifecycleEvent.before_skill,
            result=HookResult(action=HookAction.MODIFY, modifications={"ctx": {"b": 2}}, reason="mod2"),
            priority=1,
        )
        h3 = _TestHook("cont", LifecycleEvent.before_skill, priority=2)
        registry.register(h1)
        registry.register(h2)
        registry.register(h3)
        executor = HookExecutor(registry)
        result = await executor.run_pipeline(LifecycleEvent.before_skill, {})
        assert result.action == HookAction.MODIFY
        assert result.modifications == {"ctx": {"a": 1, "b": 2}}
        assert h1.executed
        assert h2.executed
        assert h3.executed

    @pytest.mark.asyncio
    async def test_retry_captured(self) -> None:
        registry = HookRegistry()
        h1 = _TestHook(
            "retry", LifecycleEvent.before_tool,
            result=HookResult(action=HookAction.RETRY, reason="retry needed"),
        )
        h2 = _TestHook("cont", LifecycleEvent.before_tool)
        registry.register(h1)
        registry.register(h2)
        executor = HookExecutor(registry)
        result = await executor.run_pipeline(LifecycleEvent.before_tool, {})
        assert result.action == HookAction.RETRY
        assert result.reason == "retry needed"

    @pytest.mark.asyncio
    async def test_approval_required_halts(self) -> None:
        registry = HookRegistry()
        h1 = _TestHook(
            "approval", LifecycleEvent.before_tool,
            result=HookResult(action=HookAction.APPROVAL_REQUIRED, reason="need approval"),
        )
        h2 = _TestHook("after", LifecycleEvent.before_tool)
        registry.register(h1)
        registry.register(h2)
        executor = HookExecutor(registry)
        result = await executor.run_pipeline(LifecycleEvent.before_tool, {})
        assert result.action == HookAction.APPROVAL_REQUIRED
        assert "need approval" in result.reason
        assert not h2.executed

    @pytest.mark.asyncio
    async def test_hook_exception_returns_block(self) -> None:
        registry = HookRegistry()

        class _FailingHook(BaseHook):
            def __init__(self) -> None:
                super().__init__(
                    HookMetadata(name="fail", description="", lifecycle_event=LifecycleEvent.before_request)
                )

            async def execute(self, context: dict) -> HookResult:
                raise ValueError("something broke")

        registry.register(_FailingHook())
        executor = HookExecutor(registry)
        result = await executor.run_pipeline(LifecycleEvent.before_request, {})
        assert result.action == HookAction.BLOCK
        assert "something broke" in result.reason


class TestHookManager:
    @pytest.mark.asyncio
    async def test_run_pipeline_delegates(self) -> None:
        registry = HookRegistry()
        h = _TestHook("h", LifecycleEvent.before_request)
        registry.register(h)
        manager = HookManager(registry)
        result = await manager.run_pipeline(LifecycleEvent.before_request, {})
        assert result.action == HookAction.CONTINUE

    @pytest.mark.asyncio
    async def test_run_pipeline_default_context(self) -> None:
        registry = HookRegistry()
        manager = HookManager(registry)
        result = await manager.run_pipeline(LifecycleEvent.before_request)
        assert result.action == HookAction.CONTINUE

    def test_registry_property(self) -> None:
        registry = HookRegistry()
        manager = HookManager(registry)
        assert manager.registry is registry


class TestRequestValidationHook:
    @pytest.mark.asyncio
    async def test_sql_injection_blocked(self) -> None:
        hook = RequestValidationHook()
        result = await hook.execute({"payload": "SELECT * FROM users WHERE id=1"})
        assert result.action == HookAction.BLOCK
        assert "SQL injection" in result.reason

    @pytest.mark.asyncio
    async def test_normal_payload_allowed(self) -> None:
        hook = RequestValidationHook()
        result = await hook.execute({"payload": "Hello, world!"})
        assert result.action == HookAction.CONTINUE

    @pytest.mark.asyncio
    async def test_json_content_type_allowed(self) -> None:
        hook = RequestValidationHook()
        result = await hook.execute({"payload": "test", "headers": {"content-type": "application/json"}})
        assert result.action == HookAction.CONTINUE


class TestSecurityHook:
    @pytest.mark.asyncio
    async def test_xss_blocked(self) -> None:
        hook = SecurityHook()
        result = await hook.execute({"payload": "<script>alert('xss')</script>"})
        assert result.action == HookAction.BLOCK
        assert "XSS" in result.reason

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self) -> None:
        hook = SecurityHook()
        result = await hook.execute({"payload": "../../etc/passwd"})
        assert result.action == HookAction.BLOCK
        assert "path traversal" in result.reason

    @pytest.mark.asyncio
    async def test_clean_payload_allowed(self) -> None:
        hook = SecurityHook()
        result = await hook.execute({"payload": "Hello, world!"})
        assert result.action == HookAction.CONTINUE

    @pytest.mark.asyncio
    async def test_xss_in_query_params_blocked(self) -> None:
        hook = SecurityHook()
        result = await hook.execute({"payload": "", "query_params": {"q": "<script>evil()</script>"}})
        assert result.action == HookAction.BLOCK
        assert "XSS" in result.reason


class TestToolPermissionHook:
    @pytest.mark.asyncio
    async def test_allowed_tool(self) -> None:
        hook = ToolPermissionHook()
        result = await hook.execute({"tool_name": "web_search"})
        assert result.action == HookAction.CONTINUE
        assert result.modifications.get("tool_allowed") is True

    @pytest.mark.asyncio
    async def test_denied_tool_blocked(self) -> None:
        hook = ToolPermissionHook()
        result = await hook.execute({"tool_name": "shell_execution"})
        assert result.action == HookAction.BLOCK
        assert "denied" in result.reason

    @pytest.mark.asyncio
    async def test_unknown_tool_blocked(self) -> None:
        hook = ToolPermissionHook()
        result = await hook.execute({"tool_name": "unknown_tool"})
        assert result.action == HookAction.BLOCK
        assert "not in the allowed tools list" in result.reason

    @pytest.mark.asyncio
    async def test_no_tool_name_blocked(self) -> None:
        hook = ToolPermissionHook()
        result = await hook.execute({})
        assert result.action == HookAction.BLOCK


class TestLoggingHook:
    @pytest.mark.asyncio
    async def test_always_continues(self) -> None:
        for event in [LifecycleEvent.before_request, LifecycleEvent.after_skill, LifecycleEvent.before_tool]:
            hook = LoggingHook(event)
            result = await hook.execute({"_start_time": __import__("time").time()})
            assert result.action == HookAction.CONTINUE


class TestOutputValidationHook:
    @pytest.mark.asyncio
    async def test_oversized_output_truncated(self) -> None:
        hook = OutputValidationHook()
        large_output = "x" * 1_500_000
        result = await hook.execute({"output": large_output})
        assert result.action == HookAction.MODIFY
        assert result.modifications.get("truncated") is True

    @pytest.mark.asyncio
    async def test_sensitive_pattern_blocked(self) -> None:
        hook = OutputValidationHook()
        result = await hook.execute({
            "output": "My API key is sk-1234",
            "sensitive_patterns": ["sk-"],
        })
        assert result.action == HookAction.BLOCK
        assert "sensitive" in result.reason

    @pytest.mark.asyncio
    async def test_normal_output_allowed(self) -> None:
        hook = OutputValidationHook()
        result = await hook.execute({"output": "Hello, world!"})
        assert result.action == HookAction.CONTINUE


class TestHumanApprovalHook:
    @pytest.mark.asyncio
    async def test_requires_approval_for_python(self) -> None:
        hook = HumanApprovalHook()
        result = await hook.execute({"tool_name": "python_executor"})
        assert result.action == HookAction.APPROVAL_REQUIRED
        assert result.modifications.get("approval", {}).get("required") is True

    @pytest.mark.asyncio
    async def test_allows_other_tools(self) -> None:
        hook = HumanApprovalHook()
        result = await hook.execute({"tool_name": "web_search"})
        assert result.action == HookAction.CONTINUE

    @pytest.mark.asyncio
    async def test_empty_tool_name_continues(self) -> None:
        hook = HumanApprovalHook()
        result = await hook.execute({})
        assert result.action == HookAction.CONTINUE


@pytest.mark.asyncio
async def test_all_hooks_loaded_integration() -> None:
    manager = HookManager()
    manager.registry.register(RequestValidationHook())
    manager.registry.register(SecurityHook())
    manager.registry.register(ToolPermissionHook())
    manager.registry.register(HumanApprovalHook())
    manager.registry.register(OutputValidationHook())
    for event in LifecycleEvent:
        manager.registry.register(LoggingHook(event))

    count = manager.registry.count
    assert count == 17  # 5 custom + 12 logging for each lifecycle event
    assert len(manager.registry.get_for_event(LifecycleEvent.before_request)) == 3  # request_validation, security, logging
    assert len(manager.registry.get_for_event(LifecycleEvent.before_tool)) == 3  # tool_permission, human_approval, logging
