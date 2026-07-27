from app.hooks.base import BaseHook, HookAction, HookMetadata, HookResult, LifecycleEvent

_APPROVAL_REQUIRED_TOOLS: set[str] = {"python_executor"}


class HumanApprovalHook(BaseHook):
    def __init__(self) -> None:
        super().__init__(
            HookMetadata(
                name="human_approval",
                description="Pauses execution for human approval on high-risk operations",
                lifecycle_event=LifecycleEvent.before_tool,
                priority=-10,
            )
        )

    async def execute(self, context: dict) -> HookResult:
        tool_name = context.get("tool_name", "")
        if not tool_name:
            return HookResult(action=HookAction.CONTINUE)
        if tool_name in _APPROVAL_REQUIRED_TOOLS:
            return HookResult(
                action=HookAction.APPROVAL_REQUIRED,
                modifications={
                    "approval": {
                        "required": True,
                        "tool_name": tool_name,
                        "reasoning": context.get("reasoning", ""),
                        "inputs": context.get("tool_inputs", {}),
                    }
                },
                reason=f"Human approval required before executing tool '{tool_name}'",
            )
        return HookResult(action=HookAction.CONTINUE)
