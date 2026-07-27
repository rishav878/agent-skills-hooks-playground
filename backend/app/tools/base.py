from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ToolPermission(str, Enum):
    ALWAYS_ALLOW = "ALWAYS_ALLOW"
    REQUIRE_CONFIRM = "REQUIRE_CONFIRM"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


@dataclass
class ToolMetadata:
    name: str
    description: str
    version: str = "1.0.0"
    risk_level: RiskLevel = RiskLevel.LOW
    permission: ToolPermission = ToolPermission.ALWAYS_ALLOW
    timeout_seconds: int = 30
    enabled: bool = True
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolInput:
    parameters: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolOutput:
    success: bool
    result: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    def __init__(self, metadata: ToolMetadata) -> None:
        self._metadata = metadata

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    @abstractmethod
    async def execute(self, input_data: ToolInput) -> ToolOutput: ...
