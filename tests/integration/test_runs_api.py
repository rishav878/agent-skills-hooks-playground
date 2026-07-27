import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.usefixtures("client")
class TestRunsAPI:
    async def test_list_runs_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert "runs" in data
        assert "total" in data

    async def test_get_run_not_found(self, client: AsyncClient) -> None:
        resp = await client.get(f"/api/v1/runs/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_get_run_events_not_found(self, client: AsyncClient) -> None:
        resp = await client.get(f"/api/v1/runs/{uuid.uuid4()}/events")
        assert resp.status_code == 200
        data = resp.json()
        assert data["events"] == []
        assert data["total"] == 0

    async def test_list_runs_pagination(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/runs?limit=5&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["runs"], list)
        assert data["total"] <= 5

    async def test_run_with_agent_then_fetch(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/agents/run",
            json={"task": "research AI safety"},
        )
        assert resp.status_code == 200
        data = resp.json()
        run_id = data["run_id"]
        assert run_id

        resp2 = await client.get(f"/api/v1/runs/{run_id}")
        assert resp2.status_code == 200
        run_data = resp2.json()
        assert run_data["id"] == run_id

        resp3 = await client.get(f"/api/v1/runs/{run_id}/events")
        assert resp3.status_code == 200
        events_data = resp3.json()
        assert events_data["total"] > 0
        event_types = [e["event_type"] for e in events_data["events"]]
        assert "request_received" in event_types

    async def test_multiple_runs_listed(self, client: AsyncClient) -> None:
        await client.post(
            "/api/v1/agents/run",
            json={"task": "research AI safety"},
        )
        await client.post(
            "/api/v1/agents/run",
            json={"task": "analyze data"},
        )
        resp = await client.get("/api/v1/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2

    async def test_run_detail_fields(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/agents/run",
            json={"task": "review code"},
        )
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]

        resp2 = await client.get(f"/api/v1/runs/{run_id}")
        data = resp2.json()
        assert "id" in data
        assert "trace_id" in data
        assert "status" in data
        assert "input" in data
        assert "created_at" in data

    async def test_event_response_fields(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/agents/run",
            json={"task": "research AI safety"},
        )
        run_id = resp.json()["run_id"]

        resp2 = await client.get(f"/api/v1/runs/{run_id}/events")
        data = resp2.json()
        if data["events"]:
            ev = data["events"][0]
            assert "id" in ev
            assert "run_id" in ev
            assert "event_type" in ev
            assert "component" in ev
            assert "status" in ev
            assert "timestamp" in ev

    async def test_event_ordered_by_timestamp(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/agents/run",
            json={"task": "research AI safety"},
        )
        run_id = resp.json()["run_id"]

        resp2 = await client.get(f"/api/v1/runs/{run_id}/events")
        data = resp2.json()
        timestamps = [e["timestamp"] for e in data["events"]]
        assert timestamps == sorted(timestamps)
