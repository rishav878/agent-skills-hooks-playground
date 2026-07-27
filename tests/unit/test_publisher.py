import uuid
from datetime import datetime, timezone

import pytest

from app.core.events import AgentEvent, Component, EventType, Status
from app.core.publisher import EventPublisher, EventSubscriber, get_publisher, set_publisher


class CollectingSubscriber(EventSubscriber):
    def __init__(self) -> None:
        self.events: list[AgentEvent] = []

    async def on_event(self, event: AgentEvent) -> None:
        self.events.append(event)


@pytest.fixture
def sample_event() -> AgentEvent:
    return AgentEvent(
        event_id=str(uuid.uuid4()),
        run_id="run-1",
        trace_id="trace-1",
        timestamp=datetime.now(timezone.utc),
        event_type=EventType.skill_started,
        component=Component.skill,
        status=Status.running,
    )


class TestEventPublisher:
    @pytest.mark.asyncio
    async def test_publish_delivers_to_subscriber(self, sample_event: AgentEvent) -> None:
        pub = EventPublisher()
        sub = CollectingSubscriber()
        pub.subscribe("run-1", sub)
        await pub.publish(sample_event)
        assert len(sub.events) == 1
        assert sub.events[0].event_id == sample_event.event_id

    @pytest.mark.asyncio
    async def test_publish_only_delivers_to_matching_run(self, sample_event: AgentEvent) -> None:
        pub = EventPublisher()
        sub1 = CollectingSubscriber()
        sub2 = CollectingSubscriber()
        pub.subscribe("run-1", sub1)
        pub.subscribe("run-2", sub2)
        await pub.publish(sample_event)
        assert len(sub1.events) == 1
        assert len(sub2.events) == 0

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_subscriber(self, sample_event: AgentEvent) -> None:
        pub = EventPublisher()
        sub = CollectingSubscriber()
        pub.subscribe("run-1", sub)
        pub.unsubscribe("run-1", sub)
        await pub.publish(sample_event)
        assert len(sub.events) == 0

    @pytest.mark.asyncio
    async def test_subscriber_count(self) -> None:
        pub = EventPublisher()
        sub1 = CollectingSubscriber()
        sub2 = CollectingSubscriber()
        assert pub.subscriber_count("run-1") == 0
        pub.subscribe("run-1", sub1)
        assert pub.subscriber_count("run-1") == 1
        pub.subscribe("run-1", sub2)
        assert pub.subscriber_count("run-1") == 2
        pub.unsubscribe("run-1", sub1)
        assert pub.subscriber_count("run-1") == 1

    @pytest.mark.asyncio
    async def test_subscriber_exception_does_not_block(self, sample_event: AgentEvent) -> None:
        pub = EventPublisher()
        class FailingSubscriber(EventSubscriber):
            async def on_event(self, event: AgentEvent) -> None:
                raise RuntimeError("oops")
        sub = FailingSubscriber()
        pub.subscribe("run-1", sub)
        await pub.publish(sample_event)

    @pytest.mark.asyncio
    async def test_get_publisher_singleton(self) -> None:
        set_publisher(EventPublisher())
        p1 = get_publisher()
        p2 = get_publisher()
        assert p1 is p2

    @pytest.mark.asyncio
    async def test_publish_to_nonexistent_run_does_nothing(self, sample_event: AgentEvent) -> None:
        pub = EventPublisher()
        await pub.publish(sample_event)
