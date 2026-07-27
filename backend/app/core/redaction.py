import re
from typing import Any

SENSITIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password|credential)\s*[:=]\s*['\"]?\S+"),
    re.compile(r"(?i)(Bearer\s+)[a-zA-Z0-9._-]+"),
    re.compile(r"(?i)(sk-[a-zA-Z0-9]{20,})"),
    re.compile(r"(?i)(AIza[a-zA-Z0-9_-]{35,})"),
    re.compile(r"\b\d{15,16}\b"),
    re.compile(r"(?i)(x-api-key|x-auth-token|authorization)\s*[:=]\s*\S+"),
]


class SecretRedactor:
    def __init__(self, patterns: list[re.Pattern[str]] | None = None) -> None:
        self._patterns = patterns or SENSITIVE_PATTERNS

    def redact(self, data: dict[str, Any] | None) -> dict[str, Any] | None:
        if data is None:
            return None
        return self._redact_dict(data)

    def _redact_dict(self, d: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in d.items():
            result[key] = self._redact_value(key, value)
        return result

    def _redact_value(self, key: str, value: Any) -> Any:
        if isinstance(value, dict):
            return self._redact_dict(value)
        if isinstance(value, str):
            return self._redact_string(value)
        if isinstance(value, list):
            return [self._redact_value(key, item) for item in value]
        return value

    def _redact_string(self, s: str) -> str:
        for pattern in self._patterns:
            s = pattern.sub("***REDACTED***", s)
        return s


redactor = SecretRedactor()
