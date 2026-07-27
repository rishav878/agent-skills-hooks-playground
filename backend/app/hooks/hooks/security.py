import re

from app.hooks.base import BaseHook, HookAction, HookMetadata, HookResult, LifecycleEvent

_XSS_PATTERN = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
_PATH_TRAVERSAL_PATTERN = re.compile(r"\.\.(?:\\|/|%2f|%5c)", re.IGNORECASE)
# Prompt injection patterns
_PROMPT_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)(ignore|disregard|forget|override)\s+(all\s+)?(previous|above|prior)\s+(instructions|prompts|directions)"),
    re.compile(r"(?i)(system\s*(prompt|message|instruction)|new\s*(instructions|prompt))"),
    re.compile(r"(?i)(you are (now|not )|from now on|act as |role.?play)"),
    re.compile(r"(?i)\b(DAN|jailbreak|bypass|breach|crack)\b"),
]


class SecurityHook(BaseHook):
    def __init__(self) -> None:
        super().__init__(
            HookMetadata(
                name="security",
                description="Scans requests for XSS and path traversal attacks",
                lifecycle_event=LifecycleEvent.before_request,
                priority=-90,
            )
        )

    async def execute(self, context: dict) -> HookResult:
        payload = context.get("payload", "")
        if isinstance(payload, str):
            if _XSS_PATTERN.search(payload):
                return HookResult(
                    action=HookAction.BLOCK,
                    reason="Request blocked: XSS pattern detected in payload",
                )
            if _PATH_TRAVERSAL_PATTERN.search(payload):
                return HookResult(
                    action=HookAction.BLOCK,
                    reason="Request blocked: path traversal detected in payload",
                )
            for pattern in _PROMPT_INJECTION_PATTERNS:
                if pattern.search(payload):
                    return HookResult(
                        action=HookAction.BLOCK,
                        reason="Request blocked: potential prompt injection detected",
                    )
        query_params = context.get("query_params", {})
        for key, value in query_params.items():
            if isinstance(value, str) and _XSS_PATTERN.search(value):
                    return HookResult(
                        action=HookAction.BLOCK,
                        reason=f"Request blocked: XSS pattern in query param '{key}'",
                    )
        return HookResult(action=HookAction.CONTINUE)
