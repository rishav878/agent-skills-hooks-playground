import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import AgentEvent, Component, EventType, Status
from app.core.publisher import EventPublisher
from app.core.service import EventService


class CapturingPublisher(EventPublisher):
    def __init__(self) -> None:
        super().__init__()
        self.published: list[AgentEvent] = []

    async def publish(self, event: AgentEvent) -> None:
        self.published.append(event)
        await super().publish(event)


@pytest.mark.asyncio
@pytest.mark.usefixtures("db_session")
class TestEventService:
    async def test_create_run(self, db_session: AsyncSession) -> None:
        svc = EventService(db_session)
        run = await svc.create_run("run-1", "trace-1", "test task")
        assert run.id == "run-1"
        assert run.trace_id == "trace-1"
        assert run.input == "test task"
        assert run.status == "pending"

    async def test_get_run_exists(self, db_session: AsyncSession) -> None:
        svc = EventService(db_session)
        await svc.create_run("run-2", "trace-2", "get test")
        run = await svc.get_run("run-2")
        assert run is not None
        assert run.id == "run-2"

    async def test_get_run_not_found(self, db_session: AsyncSession) -> None:
        svc = EventService(db_session)
        run = await svc.get_run("nonexistent")
        assert run is None

    async def test_update_run_status(self, db_session: AsyncSession) -> None:
        svc = EventService(db_session)
        await svc.create_run("run-3", "trace-3", "update test")
        await svc.update_run_status("run-3", "completed")
        run = await svc.get_run("run-3")
        assert run is not None
        assert run.status == "completed"

    async def test_save_and_publish_event(self, db_session: AsyncSession) -> None:
        publisher = CapturingPublisher()
        svc = EventService(db_session, publisher=publisher)
        await svc.create_run("run-4", "trace-4", "event test")

        event = AgentEvent(
            event_id=str(uuid.uuid4()),
            run_id="run-4",
            trace_id="trace-4",
            timestamp=datetime.now(timezone.utc),
            event_type=EventType.skill_started,
            component=Component.skill,
            status=Status.running,
            input={"task": "test"},
            output=None,
            duration_ms=100,
        )
        await svc.save_and_publish(event)

        assert len(publisher.published) == 1
        assert publisher.published[0].event_id == event.event_id

        events = await svc.get_events_by_run("run-4")
        assert len(events) == 1
        assert events[0].event_type == "skill_started"

    async def test_save_and_publish_multiple(self, db_session: AsyncSession) -> None:
        publisher = CapturingPublisher()
        svc = EventService(db_session, publisher=publisher)
        await svc.create_run("run-5", "trace-5", "multi")

        for i in range(3):
            event = AgentEvent(
                event_id=str(uuid.uuid4()),
                run_id="run-5",
                trace_id="trace-5",
                timestamp=datetime.now(timezone.utc),
                event_type=EventType.skill_completed,
                component=Component.skill,
                status=Status.completed,
            )
            await svc.save_and_publish(event)

        events = await svc.get_events_by_run("run-5")
        assert len(events) == 3

    async def test_get_all_runs(self, db_session: AsyncSession) -> None:
        svc = EventService(db_session)
        await svc.create_run("r1", "t1", "first")
        await svc.create_run("r2", "t2", "second")
        runs = await svc.get_all_runs()
        ids = [r.id for r in runs]
        assert "r1" in ids
        assert "r2" in ids

    async def test_get_all_runs_pagination(self, db_session: AsyncSession) -> None:
        svc = EventService(db_session)
        await svc.create_run("r3", "t3", "a")
        await svc.create_run("r4", "t4", "b")
        runs = await svc.get_all_runs(limit=1)
        assert len(runs) <= 1

    async def test_save_and_publish_redacts_input(self, db_session: AsyncSession) -> None:
        svc = EventService(db_session)
        await svc.create_run("run-6", "trace-6", "secret test")

        event = AgentEvent(
            event_id=str(uuid.uuid4()),
            run_id="run-6",
            trace_id="trace-6",
            timestamp=datetime.now(timezone.utc),
            event_type=EventType.request_received,
            component=Component.api,
            status=Status.running,
            input={"api_key": "sk-1234567890abcdef123456"},
        )
        await svc.save_and_publish(event)

        events = await svc.get_events_by_run("run-6")
        inp = json.loads(events[0].input)
        assert inp["api_key"] != "sk-1234567890abcdef"

    async def test_save_and_publish_error(self, db_session: AsyncSession) -> None:
        svc = EventService(db_session)
        await svc.create_run("run-7", "trace-7", "error test")

        event = AgentEvent(
            event_id=str(uuid.uuid4()),
            run_id="run-7",
            trace_id="trace-7",
            timestamp=datetime.now(timezone.utc),
            event_type=EventType.error,
            component=Component.runtime,
            status=Status.failed,
            error={"message": "something broke"},
        )
        await svc.save_and_publish(event)

        events = await svc.get_events_by_run("run-7")
        assert len(events) == 1
        assert "something broke" in events[0].error

    async def test_publish_with_metadata(self, db_session: AsyncSession) -> None:
        svc = EventService(db_session)
        await svc.create_run("run-8", "trace-8", "meta test")

        event = AgentEvent(
            event_id=str(uuid.uuid4()),
            run_id="run-8",
            trace_id="trace-8",
            timestamp=datetime.now(timezone.utc),
            event_type=EventType.skill_selected,
            component=Component.skill,
            status=Status.completed,
            metadata={"confidence": 0.95, "skill": "research"},
        )
        await svc.save_and_publish(event)

        events = await svc.get_events_by_run("run-8")
        meta = json.loads(events[0].metadata_)
        assert meta["confidence"] == 0.95
        assert meta["skill"] == "research"
