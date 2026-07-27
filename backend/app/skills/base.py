from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillMetadata:
    name: str
    description: str
    version: str
    instructions: str
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    allowed_tools: list[str] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class SkillDefinition:
    id: str
    metadata: SkillMetadata


@dataclass
class SkillInput:
    task: str
    parameters: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillOutput:
    result: Any
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseSkill(ABC):
    def __init__(self, metadata: SkillMetadata) -> None:
        self._metadata = metadata

    @property
    def metadata(self) -> SkillMetadata:
        return self._metadata

    @abstractmethod
    async def execute(self, input_data: SkillInput) -> SkillOutput: ...


@dataclass
class SkillSelection:
    skill_id: str
    skill_name: str
    confidence: float
    reasoning: str
