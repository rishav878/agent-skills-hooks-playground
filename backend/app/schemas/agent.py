from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    task: str = Field(..., max_length=10_000)
    parameters: dict = Field(default_factory=dict)


class EventSummary(BaseModel):
    event_id: str
    event_type: str
    component: str
    status: str
    timestamp: str


class AgentRunResponse(BaseModel):
    run_id: str
    trace_id: str | None = None
    task: str | None = None
    skill_used: str | None = None
    result: dict | str | list | None = None
    status: str
    error: str | None = None
    retry_count: int = 0
    events: list[EventSummary] = []
