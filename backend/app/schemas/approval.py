from datetime import datetime

from pydantic import BaseModel


class ApprovalRequestResponse(BaseModel):
    id: str
    run_id: str
    skill_name: str
    input_summary: str
    asker: str
    reason: str | None = None
    status: str
    created_at: datetime
    decided_at: datetime | None = None


class ApproveResponse(BaseModel):
    run_id: str
    approval_id: str
    status: str
    result: dict | str | list | None = None
    error: str | None = None
    events: list[dict] = []


class CancelResponse(BaseModel):
    run_id: str
    approval_id: str
    status: str
