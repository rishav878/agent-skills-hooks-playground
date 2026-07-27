import time
from typing import Any

import requests

API_BASE = "http://localhost:8000/api/v1"

_session = requests.Session()


def set_api_base(url: str) -> None:
    global API_BASE
    API_BASE = url.rstrip("/") + "/api/v1"


def _get(path: str) -> dict[str, Any]:
    resp = _session.get(f"{API_BASE}{path}", timeout=30)
    resp.raise_for_status()
    return resp.json()


def _post(path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
    resp = _session.post(f"{API_BASE}{path}", json=json or {}, timeout=120)
    resp.raise_for_status()
    return resp.json()


def health() -> dict[str, Any]:
    return _get("/health")


def list_skills() -> dict[str, Any]:
    return _get("/skills")


def get_skill(skill_id: str) -> dict[str, Any]:
    return _get(f"/skills/{skill_id}")


def list_hooks() -> dict[str, Any]:
    return _get("/hooks")


def get_hook(hook_id: str) -> dict[str, Any]:
    return _get(f"/hooks/{hook_id}")


def list_tools() -> dict[str, Any]:
    return _get("/tools")


def get_tool(tool_id: str) -> dict[str, Any]:
    return _get(f"/tools/{tool_id}")


def run_agent(task: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
    return _post("/agents/run", json={"task": task, "parameters": parameters or {}})


def list_runs(limit: int = 50, offset: int = 0) -> dict[str, Any]:
    return _get(f"/runs?limit={limit}&offset={offset}")


def get_run(run_id: str) -> dict[str, Any]:
    return _get(f"/runs/{run_id}")


def get_run_events(run_id: str, limit: int = 200, offset: int = 0) -> dict[str, Any]:
    return _get(f"/runs/{run_id}/events?limit={limit}&offset={offset}")


WEBSOCKET_URL = "ws://localhost:8000/api/v1/runs/ws"


def approve_run(run_id: str) -> dict[str, Any]:
    return _post(f"/runs/{run_id}/approve")


def cancel_run(run_id: str) -> dict[str, Any]:
    return _post(f"/runs/{run_id}/cancel")


def poll_run(run_id: str, interval: float = 0.5, max_wait: float = 60.0) -> dict[str, Any]:
    deadline = time.monotonic() + max_wait
    while time.monotonic() < deadline:
        run = get_run(run_id)
        if run["status"] in ("completed", "failed", "cancelled"):
            return run
        time.sleep(interval)
    return get_run(run_id)
