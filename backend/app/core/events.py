from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EventType(str, Enum):
    request_received = "request_received"
    hook_started = "hook_started"
    hook_completed = "hook_completed"
    skill_selected = "skill_selected"
    skill_started = "skill_started"
    skill_completed = "skill_completed"
    llm_started = "llm_started"
    llm_completed = "llm_completed"
    tool_started = "tool_started"
    tool_completed = "tool_completed"
    approval_required = "approval_required"
    approval_granted = "approval_granted"
    approval_denied = "approval_denied"
    retry_started = "retry_started"
    error = "error"
    response_generated = "response_generated"
    run_completed = "run_completed"


class Component(str, Enum):
    agent = "agent"
    skill = "skill"
    hook = "hook"
    tool = "tool"
    llm = "llm"
    api = "api"
    runtime = "runtime"
    system = "system"


class Status(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    blocked = "blocked"
    waiting_approval = "waiting_approval"
    approved = "approved"
    rejected = "rejected"


class AgentEvent(BaseModel):
    event_id: str
    run_id: str
    trace_id: str
    timestamp: datetime
    event_type: EventType
    component: Component
    status: Status
    duration_ms: int | None = None
    input: dict | None = None
    output: dict | None = None
    error: dict | None = None
    metadata: dict = Field(default_factory=dict)
