# API Reference

All endpoints are prefixed with `/api/v1`. All request/response bodies are JSON.

## Health

### `GET /api/v1/health`

Returns service health status.

**Response:**
```json
{
    "status": "ok",
    "version": "0.1.0"
}
```

## Skills

### `GET /api/v1/skills`

Lists all registered skills.

**Response:**
```json
{
    "skills": [
        {
            "id": "research",
            "metadata": {
                "name": "research",
                "description": "Research a topic using web search...",
                "version": "1.0.0",
                "input_schema": { "type": "object", "properties": { ... } },
                "output_schema": { "type": "object", "properties": { ... } },
                "allowed_tools": ["web_search"],
                "enabled": true
            }
        }
    ],
    "total": 3
}
```

### `GET /api/v1/skills/{skill_id}`

Gets a single skill by ID or name.

**Response:** Same schema as individual skill object above.

**Error:** `404` if skill not found.

## Hooks

### `GET /api/v1/hooks`

Lists all registered hooks.

**Response:**
```json
{
    "hooks": [
        {
            "hook_id": "request_validation",
            "metadata": {
                "name": "request_validation",
                "description": "Validates incoming requests...",
                "lifecycle_event": "before_request",
                "priority": -100,
                "enabled": true,
                "metadata": {}
            }
        }
    ],
    "total": 18
}
```

### `GET /api/v1/hooks/{hook_id}`

Gets a single hook by name.

**Response:** Same schema as individual hook object above.

**Error:** `404` if hook not found.

## Tools

### `GET /api/v1/tools`

Lists all registered tools.

**Response:**
```json
{
    "tools": [
        {
            "id": "web_search",
            "metadata": {
                "name": "web_search",
                "description": "Search the web for information on a given query",
                "version": "1.0.0",
                "risk_level": "LOW",
                "permission": "ALWAYS_ALLOW",
                "timeout_seconds": 30,
                "enabled": true,
                "input_schema": { "type": "object", "properties": { ... } },
                "output_schema": { "type": "object", "properties": { ... } }
            }
        }
    ],
    "total": 3
}
```

### `GET /api/v1/tools/{tool_id}`

Gets a single tool by ID or name.

**Response:** Same schema as individual tool object above.

**Error:** `404` if tool not found.

## Architecture

```text
User
  |
  v
FastAPI (REST)
  |-- GET  /api/v1/health
  |-- GET  /api/v1/skills
  |-- GET  /api/v1/skills/{skill_id}
  |-- GET  /api/v1/hooks
  |-- GET  /api/v1/hooks/{hook_id}
  |-- GET  /api/v1/tools
  |-- GET  /api/v1/tools/{tool_id}
  |-- POST /api/v1/agents/run       (planned)
  |-- GET  /api/v1/runs/{run_id}    (planned)
  |-- POST /api/v1/runs/{run_id}/approve  (planned)
  |-- WS   /ws/runs/{run_id}        (planned)
```
