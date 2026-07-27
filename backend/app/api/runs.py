import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.publisher import get_publisher
from app.core.service import EventService
from app.core.websocket_subscriber import WebSocketSubscriber
from app.database.session import get_session
from app.schemas.run import (
    EventListResponse,
    EventResponse,
    RunDetailResponse,
    RunListResponse,
    RunSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runs", tags=["runs"])


def _get_event_service(session: AsyncSession = Depends(get_session)) -> EventService:
    return EventService(session)


@router.get("", response_model=RunListResponse)
async def list_runs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: EventService = Depends(_get_event_service),
) -> RunListResponse:
    runs = await service.get_all_runs(limit=limit, offset=offset)
    return RunListResponse(
        runs=[
            RunSummary(
                id=r.id,
                trace_id=r.trace_id,
                status=r.status,
                selected_skill=r.selected_skill,
                error=r.error,
                retry_count=r.retry_count,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in runs
        ],
        total=len(runs),
    )


@router.get("/{run_id}", response_model=RunDetailResponse)
async def get_run(
    run_id: str,
    service: EventService = Depends(_get_event_service),
) -> RunDetailResponse:
    run = await service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return RunDetailResponse(
        id=run.id,
        trace_id=run.trace_id,
        status=run.status,
        input=run.input,
        output=run.output,
        selected_skill=run.selected_skill,
        error=run.error,
        retry_count=run.retry_count,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


@router.get("/{run_id}/events", response_model=EventListResponse)
async def get_run_events(
    run_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: EventService = Depends(_get_event_service),
) -> EventListResponse:
    raw_events = await service.get_events_by_run(run_id, limit=limit, offset=offset)
    events = []
    for e in raw_events:
        inp = json.loads(e.input) if e.input else None
        out = json.loads(e.output) if e.output else None
        meta = json.loads(e.metadata_) if e.metadata_ else None
        events.append(
            EventResponse(
                id=e.id,
                run_id=e.run_id,
                trace_id=e.trace_id,
                event_type=e.event_type,
                component=e.component,
                status=e.status,
                timestamp=e.timestamp,
                duration_ms=e.duration_ms,
                input=inp,
                output=out,
                error=e.error,
                metadata=meta,
            )
        )
    return EventListResponse(events=events, total=len(events))


@router.websocket("/ws/{run_id}")
async def run_events_ws(websocket: WebSocket, run_id: str) -> None:
    from app.security.auth import require_api_key_ws, verify_ws_origin

    if not require_api_key_ws(websocket):
        await websocket.close(code=4001, reason="Missing or invalid API key")
        return
    if not verify_ws_origin(websocket) and settings.api_key != "dev-key-change-me":
        await websocket.close(code=4001, reason="Origin not allowed")
        return

    await websocket.accept()
    publisher = get_publisher()
    subscriber = WebSocketSubscriber(websocket)
    publisher.subscribe(run_id, subscriber)
    logger.info("WebSocket connected for run %s", run_id)

    try:
        while True:
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected for run %s", run_id)
    except Exception:
        logger.exception("WebSocket error for run %s", run_id)
    finally:
        publisher.unsubscribe(run_id, subscriber)
