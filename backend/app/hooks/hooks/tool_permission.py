from app.hooks.base import BaseHook, HookAction, HookMetadata, HookResult, LifecycleEvent

_DENIED_TOOLS: set[str] = {"shell_execution", "network_scan"}


class ToolPermissionHook(BaseHook):
    def __init__(self) -> None:
        super().__init__(
            HookMetadata(
                name="tool_permission",
                description="Enforces tool allowlist/denylist policies",
                lifecycle_event=LifecycleEvent.before_tool,
                priority=-50,
            )
        )
        self._allowed_tools: set[str] = {
            "web_search",
            "python_executor",
            "file_reader",
        }

    async def execute(self, context: dict) -> HookResult:
        tool_name = context.get("tool_name", "")
        if not tool_name:
            return HookResult(
                action=HookAction.BLOCK,
                reason="Tool permission check failed: no tool_name in context",
            )
        if tool_name in _DENIED_TOOLS:
            return HookResult(
                action=HookAction.BLOCK,
                reason=f"Tool '{tool_name}' is explicitly denied",
            )
        if tool_name not in self._allowed_tools:
            return HookResult(
                action=HookAction.BLOCK,
                reason=f"Tool '{tool_name}' is not in the allowed tools list",
            )
        return HookResult(
            action=HookAction.CONTINUE,
            modifications={"tool_allowed": True, "tool_name": tool_name},
        )
