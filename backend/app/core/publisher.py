import logging

from app.core.events import AgentEvent

logger = logging.getLogger(__name__)


class EventSubscriber:
    async def on_event(self, event: AgentEvent) -> None: ...


class EventPublisher:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventSubscriber]] = {}

    def subscribe(self, run_id: str, subscriber: EventSubscriber) -> None:
        if run_id not in self._subscribers:
            self._subscribers[run_id] = []
        self._subscribers[run_id].append(subscriber)

    def unsubscribe(self, run_id: str, subscriber: EventSubscriber) -> None:
        subs = self._subscribers.get(run_id, [])
        if subscriber in subs:
            subs.remove(subscriber)
        if not subs:
            self._subscribers.pop(run_id, None)

    async def publish(self, event: AgentEvent) -> None:
        subs = self._subscribers.get(event.run_id, [])[:]
        if not subs:
            return
        for sub in subs:
            try:
                await sub.on_event(event)
            except Exception:
                logger.exception("Subscriber failed for run %s", event.run_id)

    def subscriber_count(self, run_id: str) -> int:
        return len(self._subscribers.get(run_id, []))


_publisher: EventPublisher | None = None


def get_publisher() -> EventPublisher:
    global _publisher
    if _publisher is None:
        _publisher = EventPublisher()
    return _publisher


def set_publisher(publisher: EventPublisher) -> None:
    global _publisher
    _publisher = publisher


def reset_publisher() -> None:
    global _publisher
    _publisher = None
