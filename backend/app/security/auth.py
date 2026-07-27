import hmac
import logging

from fastapi import HTTPException, Request, WebSocket
from fastapi.security import APIKeyHeader

from app.core.config import settings

logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def _validate_api_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    expected = settings.api_key
    if not expected or expected == "dev-key-change-me":
        return None
    if len(api_key) != len(expected):
        return None
    return api_key if hmac.compare_digest(api_key, expected) else None


async def require_api_key(request: Request) -> None:
    api_key = request.headers.get("X-API-Key")
    if settings.environment == "development" and settings.api_key == "dev-key-change-me":
        return
    if not _validate_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def require_api_key_ws(websocket: WebSocket) -> bool:
    api_key = websocket.headers.get("x-api-key") or websocket.query_params.get("api_key")
    if settings.environment == "development" and settings.api_key == "dev-key-change-me":
        return True
    return _validate_api_key(api_key) is not None


async def optional_api_key(request: Request) -> str | None:
    api_key = request.headers.get("X-API-Key")
    return _validate_api_key(api_key)


def verify_ws_origin(websocket: WebSocket) -> bool:
    origin = websocket.headers.get("origin", "")
    if not origin:
        return False
    allowed = settings.cors_origin_list
    if not allowed:
        return False
    return any(origin.rstrip("/") == o.rstrip("/") for o in allowed)
