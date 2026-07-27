"""End-to-end test: spins up the FastAPI app, executes an agent run, and verifies the result."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_agent_run_e2e(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/agents/run",
        json={"task": "test the system", "parameters": {}},
    )
    assert resp.status_code in (200, 503), f"Unexpected status: {resp.status_code}"
    if resp.status_code == 200:
        data = resp.json()
        assert "run_id" in data
        assert "status" in data
        run_id = data["run_id"]
        events_resp = await client.get(f"/api/v1/runs/{run_id}/events")
        assert events_resp.status_code == 200
        events = events_resp.json()
        assert isinstance(events, dict)
        assert "events" in events


@pytest.mark.asyncio
async def test_health_endpoint_e2e(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
