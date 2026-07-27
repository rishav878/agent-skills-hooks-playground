from datetime import datetime

from app.core.events import AgentEvent, Component, EventType, Status


def test_event_type_enum_values() -> None:
    assert EventType.request_received.value == "request_received"
    assert EventType.skill_started.value == "skill_started"
    assert EventType.run_completed.value == "run_completed"


def test_component_enum_values() -> None:
    assert Component.agent.value == "agent"
    assert Component.hook.value == "hook"
    assert Component.system.value == "system"


def test_status_enum_values() -> None:
    assert Status.pending.value == "pending"
    assert Status.completed.value == "completed"
    assert Status.waiting_approval.value == "waiting_approval"


def test_agent_event_defaults() -> None:
    event = AgentEvent(
        event_id="evt-001",
        run_id="run-001",
        trace_id="trace-001",
        timestamp=datetime(2026, 1, 1),
        event_type=EventType.skill_started,
        component=Component.skill,
        status=Status.running,
    )
    assert event.event_id == "evt-001"
    assert event.run_id == "run-001"
    assert event.event_type == EventType.skill_started
    assert event.duration_ms is None
    assert event.input is None
    assert event.output is None
    assert event.error is None
    assert event.metadata == {}


def test_agent_event_with_all_fields() -> None:
    event = AgentEvent(
        event_id="evt-002",
        run_id="run-001",
        trace_id="trace-001",
        timestamp=datetime(2026, 1, 1),
        event_type=EventType.tool_completed,
        component=Component.tool,
        status=Status.completed,
        duration_ms=1500,
        input={"query": "test"},
        output={"result": "ok"},
        error=None,
        metadata={"tool": "web_search"},
    )
    assert event.duration_ms == 1500
    assert event.input == {"query": "test"}
    assert event.metadata["tool"] == "web_search"


def test_event_type_count() -> None:
    assert len(EventType) == 17


def test_component_count() -> None:
    assert len(Component) == 8


def test_status_count() -> None:
    assert len(Status) == 8
