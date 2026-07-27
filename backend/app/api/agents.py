import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.events import EventEmitter
from app.agents.runtime import AgentRuntime
from app.core.service import EventService
from app.database.session import get_session
from app.schemas.agent import AgentRunRequest, AgentRunResponse, EventSummary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


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


@router.post("/run", response_model=AgentRunResponse)
async def run_agent(
    body: AgentRunRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AgentRunResponse:
    runtime = _get_runtime(request)
    service = EventService(session)

    # Pre-generate IDs so we can create the AgentRun before any events fire
    run_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())

    await service.create_run(run_id, trace_id, body.task)

    emitter = EventEmitter(service)
    result = await runtime.run(
        {
            "task": body.task,
            "parameters": body.parameters,
            "run_id": run_id,
            "trace_id": trace_id,
        },
        event_emitter=emitter,
        event_service=service,
    )

    status = result.get("status", "failed")
    try:
        await service.update_run_status(run_id, status)
    except Exception:
        logger.exception("Failed to update run status for %s", run_id)

    return AgentRunResponse(
        run_id=run_id,
        trace_id=trace_id,
        task=body.task,
        skill_used=result.get("skill_used"),
        result=result.get("result"),
        status=status,
        error=result.get("error"),
        retry_count=result.get("retry_count", 0),
        events=[
            EventSummary(
                event_id=e["event_id"],
                event_type=e["event_type"],
                component=e["component"],
                status=e["status"],
                timestamp=e["timestamp"],
            )
            for e in result.get("events", [])
        ],
    )
