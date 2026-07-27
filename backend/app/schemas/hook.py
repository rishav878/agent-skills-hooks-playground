from pydantic import BaseModel

from app.hooks.base import LifecycleEvent


class HookMetadataResponse(BaseModel):
    name: str
    description: str
    lifecycle_event: LifecycleEvent
    priority: int
    enabled: bool
    metadata: dict


class HookResponse(BaseModel):
    hook_id: str
    metadata: HookMetadataResponse


class HookListResponse(BaseModel):
    hooks: list[HookResponse]
    total: int
