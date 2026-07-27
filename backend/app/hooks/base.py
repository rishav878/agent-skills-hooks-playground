from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HookAction(str, Enum):
    CONTINUE = "CONTINUE"
    BLOCK = "BLOCK"
    MODIFY = "MODIFY"
    RETRY = "RETRY"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"


class LifecycleEvent(str, Enum):
    before_request = "before_request"
    after_request = "after_request"
    before_agent = "before_agent"
    after_agent = "after_agent"
    before_skill = "before_skill"
    after_skill = "after_skill"
    before_tool = "before_tool"
    after_tool = "after_tool"
    before_llm = "before_llm"
    after_llm = "after_llm"
    before_response = "before_response"
    after_response = "after_response"


@dataclass
class HookResult:
    action: HookAction = HookAction.CONTINUE
    modifications: dict[str, Any] = field(default_factory=dict)
    reason: str = ""


@dataclass
class HookMetadata:
    name: str
    description: str
    lifecycle_event: LifecycleEvent
    priority: int = 0
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseHook(ABC):
    def __init__(self, metadata: HookMetadata) -> None:
        self._metadata = metadata

    @property
    def metadata(self) -> HookMetadata:
        return self._metadata

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> HookResult: ...
