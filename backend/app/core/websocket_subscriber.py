import json
import logging

from fastapi import WebSocket

from app.core.events import AgentEvent
from app.core.publisher import EventSubscriber

logger = logging.getLogger(__name__)


class WebSocketSubscriber(EventSubscriber):
    def __init__(self, websocket: WebSocket) -> None:
        self._ws = websocket

    async def on_event(self, event: AgentEvent) -> None:
        try:
            payload = {
                "event_id": event.event_id,
                "run_id": event.run_id,
                "trace_id": event.trace_id,
                "timestamp": event.timestamp.isoformat(),
                "event_type": event.event_type.value,
                "component": event.component.value,
                "status": event.status.value,
                "duration_ms": event.duration_ms,
                "input": event.input,
                "output": event.output,
                "error": event.error,
                "metadata": event.metadata,
            }
            await self._ws.send_text(json.dumps(payload, default=str))
        except Exception:
            logger.debug("WebSocket send failed (client may have disconnected)", exc_info=True)
