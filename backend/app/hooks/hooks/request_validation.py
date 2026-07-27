import re

from app.hooks.base import BaseHook, HookAction, HookMetadata, HookResult, LifecycleEvent

_SQL_PATTERN = re.compile(
    r"(\bSELECT\b.*\bFROM\b|\bDROP\b|\bDELETE\b.*\bFROM\b|\bINSERT\b.*\bINTO\b|\bUNION\b.*\bSELECT\b)",
    re.IGNORECASE,
)


class RequestValidationHook(BaseHook):
    def __init__(self) -> None:
        super().__init__(
            HookMetadata(
                name="request_validation",
                description="Validates incoming requests for malformed payloads and injection patterns",
                lifecycle_event=LifecycleEvent.before_request,
                priority=-100,
            )
        )

    async def execute(self, context: dict) -> HookResult:
        payload = context.get("payload", "")
        if isinstance(payload, str) and _SQL_PATTERN.search(payload):
            return HookResult(
                action=HookAction.BLOCK,
                reason="Request blocked: SQL injection pattern detected in payload",
            )
        headers = context.get("headers", {})
        content_type = headers.get("content-type", "")
        if "application/json" in content_type:
            return HookResult(action=HookAction.CONTINUE)
        if not content_type:
            return HookResult(action=HookAction.CONTINUE)
        return HookResult(
            action=HookAction.BLOCK,
            reason=f"Request blocked: unsupported content type '{content_type}'",
        )
