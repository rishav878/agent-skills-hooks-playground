from datetime import datetime

from pydantic import BaseModel


class RunSummary(BaseModel):
    id: str
    trace_id: str
    status: str
    selected_skill: str | None = None
    error: str | None = None
    retry_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None


class RunListResponse(BaseModel):
    runs: list[RunSummary]
    total: int


class RunDetailResponse(BaseModel):
    id: str
    trace_id: str
    status: str
    input: str
    output: str | None = None
    selected_skill: str | None = None
    error: str | None = None
    retry_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None


class EventResponse(BaseModel):
    id: str
    run_id: str
    trace_id: str
    event_type: str
    component: str
    status: str
    timestamp: datetime
    duration_ms: int | None = None
    input: dict | str | None = None
    output: dict | str | None = None
    error: str | None = None
    metadata: dict | None = None


class EventListResponse(BaseModel):
    events: list[EventResponse]
    total: int
