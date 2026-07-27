from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.schemas.hook import HookListResponse, HookMetadataResponse, HookResponse

router = APIRouter(prefix="/hooks", tags=["hooks"])


def _to_response(hook_id: str, hook: Any) -> HookResponse:
    return HookResponse(
        hook_id=hook_id,
        metadata=HookMetadataResponse(
            name=hook.metadata.name,
            description=hook.metadata.description,
            lifecycle_event=hook.metadata.lifecycle_event,
            priority=hook.metadata.priority,
            enabled=hook.metadata.enabled,
            metadata=dict(hook.metadata.metadata),
        ),
    )


@router.get("", response_model=HookListResponse)
async def list_hooks(request: Request) -> HookListResponse:
    manager = request.app.state.hook_manager
    hooks = manager.registry.list_all()
    items = [_to_response(h.metadata.name, h) for h in hooks]
    return HookListResponse(hooks=items, total=len(items))


@router.get("/{hook_id}", response_model=HookResponse)
async def get_hook(hook_id: str, request: Request) -> HookResponse:
    manager = request.app.state.hook_manager
    hook = manager.registry.get(hook_id)
    if hook is None:
        raise HTTPException(status_code=404, detail=f"Hook '{hook_id}' not found")
    return _to_response(hook_id, hook)
