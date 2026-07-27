from dataclasses import dataclass, field
from typing import Any

from app.core.events import AgentEvent
from app.hooks.base import HookResult
from app.skills.base import SkillOutput, SkillSelection
from app.tools.base import ToolInput, ToolOutput


@dataclass
class AgentState:
    run_id: str = ""
    trace_id: str = ""
    skill_loader: Any = None
    hook_manager: Any = None
    tool_executor: Any = None
    llm_provider: Any = None
    event_emitter: Any = None
    event_service: Any = None
    rag_engine: Any = None
    memory_service: Any = None

    request_payload: dict[str, Any] = field(default_factory=dict)
    task: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)

    skill_selection: SkillSelection | None = None
    skill_output: SkillOutput | None = None

    tool_name: str = ""
    tool_input: ToolInput | None = None
    tool_output: ToolOutput | None = None

    hook_results: list[HookResult] = field(default_factory=list)
    events: list[AgentEvent] = field(default_factory=list)
    modifications: dict[str, Any] = field(default_factory=dict)

    error: str | None = None
    retry_count: int = 0
    max_retries: int = 2
    blocked: bool = False
    approval_required: bool = False
    approval_granted: bool = False
    approval_id: str = ""
    completed: bool = False
    resumed: bool = False

    response: dict[str, Any] | None = None
