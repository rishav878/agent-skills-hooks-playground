import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.usefixtures("client")
class TestApprovalAPI:
    async def test_approve_on_non_existent_run(self, client: AsyncClient) -> None:
        resp = await client.post("/api/v1/runs/non-existent-id/approve")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data

    async def test_cancel_on_non_existent_run(self, client: AsyncClient) -> None:
        resp = await client.post("/api/v1/runs/non-existent-id/cancel")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data

    async def test_approval_required_flow_without_tool(self, client: AsyncClient) -> None:
        """A run that doesn't trigger a high-risk tool should complete normally."""
        resp = await client.post(
            "/api/v1/agents/run",
            json={"task": "analyze data", "parameters": {}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("completed", "failed")

    async def test_approval_required_flow_with_tool(self, client: AsyncClient) -> None:
        """A task that uses the data_analysis skill with use_tool=True should
        trigger approval_required and return waiting_approval status."""
        resp = await client.post(
            "/api/v1/agents/run",
            json={
                "task": "analyze data with python",
                "parameters": {"use_tool": True},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # The run should be waiting for approval
        assert data["status"] == "waiting_approval", (
            f"Expected waiting_approval, got {data['status']}: {data}"
        )
        run_id = data["run_id"]
        assert run_id

        # Verify the run exists in the DB
        resp2 = await client.get(f"/api/v1/runs/{run_id}")
        assert resp2.status_code == 200
        run_data = resp2.json()
        assert run_data["status"] == "waiting_approval"

    async def test_approve_and_resume(self, client: AsyncClient) -> None:
        """Approve a waiting run and verify it resumes and completes."""
        resp = await client.post(
            "/api/v1/agents/run",
            json={
                "task": "analyze data with python",
                "parameters": {"use_tool": True},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "waiting_approval"
        run_id = data["run_id"]

        # Approve the run
        approve_resp = await client.post(f"/api/v1/runs/{run_id}/approve")
        assert approve_resp.status_code == 200
        approve_data = approve_resp.json()
        assert approve_data["run_id"] == run_id
        assert approve_data["status"] == "completed"
        assert approve_data["approval_id"]

    async def test_cancel_run(self, client: AsyncClient) -> None:
        """Cancel a waiting run and verify it's marked as cancelled."""
        resp = await client.post(
            "/api/v1/agents/run",
            json={
                "task": "analyze data with python",
                "parameters": {"use_tool": True},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "waiting_approval"
        run_id = data["run_id"]

        # Cancel the run
        cancel_resp = await client.post(f"/api/v1/runs/{run_id}/cancel")
        assert cancel_resp.status_code == 200
        cancel_data = cancel_resp.json()
        assert cancel_data["run_id"] == run_id
        assert cancel_data["status"] == "cancelled"

        # Verify the run status is cancelled
        run_resp = await client.get(f"/api/v1/runs/{run_id}")
        assert run_resp.status_code == 200
        assert run_resp.json()["status"] == "cancelled"

    async def test_approve_already_cancelled(self, client: AsyncClient) -> None:
        """Approve on a run that was already cancelled should still work
        since the approval request is handled independently."""
        resp = await client.post(
            "/api/v1/agents/run",
            json={
                "task": "analyze data with python",
                "parameters": {"use_tool": True},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "waiting_approval"
        run_id = data["run_id"]

        # Cancel first
        await client.post(f"/api/v1/runs/{run_id}/cancel")

        # Trying to approve should now return 404 (no pending approval)
        approve_resp = await client.post(f"/api/v1/runs/{run_id}/approve")
        assert approve_resp.status_code == 404

    async def test_denied_run_events(self, client: AsyncClient) -> None:
        """Verify events exist for a cancelled run."""
        resp = await client.post(
            "/api/v1/agents/run",
            json={
                "task": "analyze data with python",
                "parameters": {"use_tool": True},
            },
        )
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]

        await client.post(f"/api/v1/runs/{run_id}/cancel")

        events_resp = await client.get(f"/api/v1/runs/{run_id}/events")
        assert events_resp.status_code == 200
        events = events_resp.json()
        assert events["total"] > 0
        event_types = {e["event_type"] for e in events["events"]}
        assert "approval_required" in event_types

    async def test_approve_run_events(self, client: AsyncClient) -> None:
        """Verify approval_granted event exists after approval."""
        resp = await client.post(
            "/api/v1/agents/run",
            json={
                "task": "analyze data with python",
                "parameters": {"use_tool": True},
            },
        )
        assert resp.status_code == 200
        run_id = resp.json()["run_id"]

        await client.post(f"/api/v1/runs/{run_id}/approve")

        events_resp = await client.get(f"/api/v1/runs/{run_id}/events")
        assert events_resp.status_code == 200
        events_data = events_resp.json()
        event_types = {e["event_type"] for e in events_data["events"]}
        assert "approval_granted" in event_types
