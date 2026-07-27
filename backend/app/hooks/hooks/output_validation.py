from app.hooks.base import BaseHook, HookAction, HookMetadata, HookResult, LifecycleEvent

_MAX_OUTPUT_SIZE = 1_000_000


class OutputValidationHook(BaseHook):
    def __init__(self) -> None:
        super().__init__(
            HookMetadata(
                name="output_validation",
                description="Validates skill/tool output for size limits and content policies",
                lifecycle_event=LifecycleEvent.after_response,
                priority=-30,
            )
        )

    async def execute(self, context: dict) -> HookResult:
        output = context.get("output", "")
        if output and isinstance(output, str) and len(output) > _MAX_OUTPUT_SIZE:
            return HookResult(
                action=HookAction.MODIFY,
                modifications={
                    "output": output[:_MAX_OUTPUT_SIZE] + "\n... (truncated)",
                    "truncated": True,
                },
                reason="Output exceeded maximum size and was truncated",
            )
        sensitive_patterns = context.get("sensitive_patterns", [])
        if isinstance(output, str) and sensitive_patterns:
            for pattern in sensitive_patterns:
                if pattern in output:
                    return HookResult(
                        action=HookAction.BLOCK,
                        reason=f"Output blocked: sensitive content matched pattern '{pattern}'",
                    )
        return HookResult(action=HookAction.CONTINUE)
