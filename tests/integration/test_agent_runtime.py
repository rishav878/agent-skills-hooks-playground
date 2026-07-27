import pytest
from httpx import AsyncClient

from app.hooks.base import LifecycleEvent
from app.hooks.hooks.human_approval import HumanApprovalHook
from app.hooks.hooks.logging_hook import LoggingHook
from app.hooks.hooks.output_validation import OutputValidationHook
from app.hooks.hooks.request_validation import RequestValidationHook
from app.hooks.hooks.security import SecurityHook
from app.hooks.hooks.tool_permission import ToolPermissionHook
from app.hooks.manager import HookManager
from app.main import app
from app.skills.loader import SkillLoader
from app.tools.loader import ToolLoader


@pytest.fixture(autouse=True)
def _setup_agent_runtime() -> None:
    skill_loader = SkillLoader()
    skill_loader.load_builtins()
    app.state.skill_loader = skill_loader

    hm = HookManager()
    hm.registry.register(RequestValidationHook())
    hm.registry.register(SecurityHook())
    hm.registry.register(ToolPermissionHook())
    hm.registry.register(HumanApprovalHook())
    hm.registry.register(OutputValidationHook())
    for event in LifecycleEvent:
        hm.registry.register(LoggingHook(event))
    app.state.hook_manager = hm

    tool_loader = ToolLoader()
    tool_loader.load_builtins()
    app.state.tool_loader = tool_loader

    yield

    app.state.skill_loader = None
    app.state.hook_manager = None
    app.state.tool_loader = None


@pytest.mark.asyncio
async def test_research_flow(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/agents/run",
        json={"task": "research quantum computing", "parameters": {}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["skill_used"] == "research"
    assert len(data["events"]) > 0
    event_types = {e["event_type"] for e in data["events"]}
    assert "request_received" in event_types
    assert "skill_selected" in event_types
    assert "skill_completed" in event_types
    assert "response_generated" in event_types
    assert "run_completed" in event_types


@pytest.mark.asyncio
async def test_data_analysis_flow(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/agents/run",
        json={"task": "analyze data with python", "parameters": {}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["skill_used"] in ("data_analysis", "code_review")


@pytest.mark.asyncio
async def test_tool_blocking(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/agents/run",
        json={"task": "research quantum computing", "parameters": {}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"

    # SQL injection in payload is blocked by RequestValidationHook at before_request
    response2 = await client.post(
        "/api/v1/agents/run",
        json={"task": "SELECT * FROM users", "parameters": {}},
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["status"] == "failed"
    event_types = {e["event_type"] for e in data2["events"]}
    assert "error" in event_types


@pytest.mark.asyncio
async def test_approval_flow(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/agents/run",
        json={
            "task": "run python print('hello')",
            "parameters": {},
        },
    )
    assert response.status_code == 200
    data = response.json()
    event_types = {e["event_type"] for e in data["events"]}
    assert "request_received" in event_types
    assert "skill_selected" in event_types


@pytest.mark.asyncio
async def test_retry_flow(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/agents/run",
        json={"task": "research something", "parameters": {}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("completed", "failed")
    assert isinstance(data["retry_count"], int)


@pytest.mark.asyncio
async def test_run_returns_events(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/agents/run",
        json={"task": "research AI safety", "parameters": {}},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) >= 6
    assert data["run_id"]
    assert data["trace_id"]


@pytest.mark.asyncio
async def test_missing_task_does_not_crash(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/agents/run",
        json={"task": "", "parameters": {}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("completed", "failed")
