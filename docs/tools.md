# Tool System

Tools represent external capabilities that agents can invoke. Each tool has
typed inputs/outputs, a risk classification, a permission model, and a configurable timeout.

## Architecture

```
ToolExecutor.execute(tool_name, input_data)
    |
    |-- ToolRegistry.get(tool_name)
    |-- Check enabled
    |-- asyncio.wait_for(tool.execute(), timeout)
    |
    v
ToolOutput(success, result, error, duration_ms)
```

## Core Components

### RiskLevel (enum)

| Level      | Meaning                                    |
|------------|--------------------------------------------|
| `LOW`      | Safe, no side effects (e.g., web search)   |
| `MEDIUM`   | May have side effects (e.g., file reader)  |
| `HIGH`     | Dangerous if misused (e.g., Python exec)   |
| `CRITICAL` | Extreme risk (reserved)                    |

### ToolPermission (enum)

| Permission           | Meaning                                          |
|----------------------|--------------------------------------------------|
| `ALWAYS_ALLOW`       | Always permitted without confirmation            |
| `REQUIRE_CONFIRM`    | User should confirm before execution             |
| `DENY`               | Never allowed                                    |
| `REQUIRE_APPROVAL`   | Requires explicit human approval                 |

### ToolMetadata

```python
@dataclass
class ToolMetadata:
    name: str
    description: str
    version: str = "1.0.0"
    risk_level: RiskLevel = RiskLevel.LOW
    permission: ToolPermission = ToolPermission.ALWAYS_ALLOW
    timeout_seconds: int = 30
    enabled: bool = True
    input_schema: dict | None = None
    output_schema: dict | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

### BaseTool (ABC)

```python
class BaseTool(ABC):
    def __init__(self, metadata: ToolMetadata) -> None: ...
    @property
    def metadata(self) -> ToolMetadata: ...
    @abstractmethod
    async def execute(self, input_data: ToolInput) -> ToolOutput: ...
```

### ToolInput / ToolOutput

```python
@dataclass
class ToolInput:
    parameters: dict[str, Any]          # Tool-specific arguments
    context: dict[str, Any]             # Execution context

@dataclass
class ToolOutput:
    success: bool
    result: Any = None
    error: str | None = None
    duration_ms: float = 0.0            # Set by ToolExecutor
    metadata: dict[str, Any]
```

## Tool Registry

The `ToolRegistry` manages tool registration and lookup:

- `register(tool)` — add a tool
- `get(tool_id)` — retrieve by name
- `list_all()` — all registered tools
- `list_enabled()` — only enabled tools
- `get_by_risk(risk)` — tools by risk level
- `get_by_permission(permission)` — tools by permission level
- `remove(tool_id)` — remove a tool
- `clear()` — remove all tools

Tools are automatically grouped by `risk_level` for efficient lookup.

## Tool Executor

The `ToolExecutor` executes tools with safety guarantees:

1. **Lookup** — tool must exist in registry
2. **Enable check** — disabled tools are rejected
3. **Timeout** — tool execution is wrapped in `asyncio.wait_for`
4. **Exception safety** — any exception is caught and returned as `ToolOutput(success=False)`
5. **Duration tracking** — `duration_ms` is set automatically

### Timeout

Each tool declares its own `timeout_seconds`. The executor enforces it via
`asyncio.wait_for`. On timeout, a `ToolOutput(success=False)` is returned
with a descriptive error.

## Built-in Tools

| Tool                  | Risk    | Permission        | Timeout | Inputs              | Outputs                 |
|-----------------------|---------|-------------------|---------|---------------------|-------------------------|
| `web_search`          | LOW     | ALWAYS_ALLOW      | 30s     | query, max_results  | results list, provider  |
| `python_executor`     | HIGH    | REQUIRE_APPROVAL  | 15s     | code                | stdout, error           |
| `file_reader`         | MEDIUM  | REQUIRE_CONFIRM   | 10s     | path                | filename, content, size |

### Web Search Tool

Searches the web using a pluggable provider. The tool uses a provider
abstraction to avoid hard-coding any search service.

**Provider abstraction (`SearchProvider`):**

```python
class SearchProvider(ABC):
    @property
    def name(self) -> str: ...
    async def search(self, query: str, max_results: int = 5) -> SearchResponse: ...
```

Available providers:
- **MockSearchProvider** — returns simulated results (default, no network)
- **DuckDuckGoSearchProvider** — uses `duckduckgo_search` library when installed

Set a custom provider at runtime:
```python
from app.tools.providers.search import DuckDuckGoSearchProvider
from app.tools.tools.web_search import set_search_provider

set_search_provider(DuckDuckGoSearchProvider())
```

**Input:**
```json
{ "query": "Python async programming", "max_results": 5 }
```

**Output:**
```json
{
    "query": "Python async programming",
    "results": [
        { "title": "...", "url": "https://...", "snippet": "..." }
    ],
    "total_results": 5,
    "provider": "mock"
}
```

### Python Execution Tool

Executes Python code in a restricted sandbox. **Never allows unrestricted
shell access** and does **not expose environment secrets**.

Security measures:
1. **AST-based safety check** before execution:
   - Blocks dangerous builtins: `__import__`, `exec`, `eval`, `compile`, `open`, `input`
   - Blocks access to dunder attributes: `__class__`, `__base__`, `__subclasses__`,
     `__globals__`, `__code__`, `__dict__`, `__builtins__`
2. **Restricted builtins** — only safe builtins are available (no `__import__`,
   no file I/O)
3. **Stdout capture** — output is captured via `StringIO`
4. **Output limit** — stdout and error are truncated at 100,000 characters

**Input:**
```json
{ "code": "print(sum(range(10)))" }
```

**Output:**
```json
{ "stdout": "45\n", "error": null }
```

### File Reader Tool

Reads file contents from the filesystem with path traversal protection.

Security measures:
- **Optional allowed directory** — when set, all paths must resolve within it
- **Path resolution** — uses `Path.resolve()` to prevent symlink attacks
- **File existence and type validation**
- **Size limit** — files over 1,000,000 bytes are rejected

**Input:**
```json
{ "path": "/workspace/data.txt" }
```

**Output:**
```json
{ "filename": "data.txt", "content": "...", "size_bytes": 1234 }
```

## Loading

Tools are loaded via `ToolLoader.load_builtins()` which registers all three
built-in tools. The loader is called during application startup and the
registry is stored in `app.state.tool_loader`.

## Testing

The tool system includes tests for:
- RiskLevel and ToolPermission enums
- ToolMetadata, ToolInput, ToolOutput dataclasses
- BaseTool ABC and concrete subclasses
- ToolRegistry (register, get, list, by_risk, by_permission, remove, clear)
- ToolExecutor (success, not found, disabled, timeout, exception)
- ToolLoader (load builtins, idempotency)
- MockSearchProvider (search, custom results)
- WebSearchTool (success, no query, default provider)
- PythonExecutionTool (simple code, syntax error, blocked builtins,
  runtime error, dunder access blocked)
- FileReaderTool (read existing, not found, path traversal prevention,
  allowed directory scoping)
