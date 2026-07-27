import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.events import EventEmitter
from app.agents.runtime import AgentRuntime
from app.agents.state import AgentState
from app.core.service import EventService
from app.database.session import get_session
from app.schemas.approval import ApproveResponse, CancelResponse
from app.skills.base import SkillOutput, SkillSelection
from app.tools.base import ToolInput

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runs", tags=["approvals"])


def _get_runtime(request: Request) -> AgentRuntime:
    skill_loader = getattr(request.app.state, "skill_loader", None)
    hook_manager = getattr(request.app.state, "hook_manager", None)
    tool_loader = getattr(request.app.state, "tool_loader", None)
    if skill_loader is None or hook_manager is None or tool_loader is None:
        raise HTTPException(status_code=503, detail="Agent runtime not initialized")
    from app.tools.executor import ToolExecutor

    executor = ToolExecutor(tool_loader.registry if tool_loader else None)
    return AgentRuntime(
        skill_loader=skill_loader,
        hook_manager=hook_manager,
        tool_executor=executor,
    )


def _get_event_service(session: AsyncSession = Depends(get_session)) -> EventService:
    return EventService(session)


@router.post("/{run_id}/approve", response_model=ApproveResponse)
async def approve_run(
    run_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ApproveResponse:
    service = EventService(session)
    runtime = _get_runtime(request)

    approval = await service.get_pending_approval(run_id)
    if approval is None:
        raise HTTPException(
            status_code=404,
            detail=f"No pending approval request found for run '{run_id}'",
        )

    try:
        snapshot = json.loads(approval.state_snapshot)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=500, detail="Corrupted approval state snapshot") from None

    approved = await service.approve_request(approval.id)
    if approved is None:
        raise HTTPException(status_code=500, detail="Failed to approve request")

    # Reconstruct AgentState from snapshot
    skill_selection = None
    ss = snapshot.get("skill_selection")
    if ss:
        skill_selection = SkillSelection(
            skill_id=ss["skill_id"],
            skill_name=ss["skill_name"],
            confidence=ss["confidence"],
            reasoning=ss["reasoning"],
        )

    skill_output = None
    so = snapshot.get("skill_output")
    if so:
        skill_output = SkillOutput(
            result=so["result"],
            summary=so.get("summary", ""),
            metadata=so.get("metadata", {}),
        )

    tool_input = None
    ti = snapshot.get("tool_input")
    if ti:
        tool_input = ToolInput(
            parameters=ti.get("parameters", {}),
            context=ti.get("context", {}),
        )

    restored = AgentState(
        run_id=snapshot.get("run_id", run_id),
        trace_id=snapshot.get("trace_id", ""),
        request_payload=snapshot.get("request_payload", {}),
        task=snapshot.get("task", ""),
        parameters=snapshot.get("parameters", {}),
        skill_selection=skill_selection,
        skill_output=skill_output,
        tool_name=snapshot.get("tool_name", ""),
        tool_input=tool_input,
        modifications=snapshot.get("modifications", {}),
        retry_count=snapshot.get("retry_count", 0),
        approval_required=True,
        approval_granted=True,
        approval_id=approval.id,
        resumed=True,
    )

    emitter = EventEmitter(service)
    result = await runtime.resume(restored, event_emitter=emitter)

    status = result.get("status", "completed")
    try:
        await service.update_run(run_id, status, output=json.dumps(result.get("result")))
    except Exception:
        logger.exception("Failed to update run status for %s", run_id)

    events_data = []
    for e in emitter.events:
        events_data.append({
            "event_id": e.event_id,
            "event_type": e.event_type.value,
            "component": e.component.value,
            "status": e.status.value,
            "timestamp": e.timestamp.isoformat(),
        })

    return ApproveResponse(
        run_id=run_id,
        approval_id=approval.id,
        status=status,
        result=result.get("result"),
        error=result.get("error"),
        events=events_data,
    )


@router.post("/{run_id}/cancel", response_model=CancelResponse)
async def cancel_run(
    run_id: str,
    session: AsyncSession = Depends(get_session),
) -> CancelResponse:
    service = EventService(session)

    approval = await service.get_pending_approval(run_id)
    if approval is None:
        raise HTTPException(
            status_code=404,
            detail=f"No pending approval request found for run '{run_id}'",
        )

    denied = await service.deny_request(approval.id)
    if denied is None:
        raise HTTPException(status_code=500, detail="Failed to deny request")

    await service.update_run(run_id, "cancelled")

    return CancelResponse(
        run_id=run_id,
        approval_id=approval.id,
        status="cancelled",
    )
