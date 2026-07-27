# Hook System

Hooks represent WHEN lifecycle logic executes. They are interception points
that run before or after key agent operations, enabling cross-cutting concerns
like validation, security, logging, access control, and human approval.

## Architecture

```
Lifecycle Event
    |
    v
HookManager.run_pipeline()
    |
    v
HookExecutor.run_pipeline()
    |-- for each hook in priority order:
    |     1. Hook.execute(context)
    |     2. Evaluate HookAction
    |     3. If BLOCK/APPROVAL_REQUIRED -> halt
    |     4. If MODIFY -> deep-merge modifications
    |     5. Accumulate RETRY/MODIFY
    |
    v
HookResult(action, modifications, reason)
```

## Core Components

### HookAction (enum)

| Action           | Meaning                                          |
|------------------|--------------------------------------------------|
| `CONTINUE`       | Proceed normally                                 |
| `BLOCK`          | Halt execution, request is rejected              |
| `MODIFY`         | Modify context data and continue                 |
| `RETRY`          | Request the calling system to retry              |
| `APPROVAL_REQUIRED` | Pause and wait for human approval           |

### LifecycleEvent (enum)

| Event             | Fires                             |
|-------------------|-----------------------------------|
| `before_request`  | Before handling an API request    |
| `after_request`   | After handling an API request     |
| `before_agent`    | Before agent execution begins     |
| `after_agent`     | After agent execution completes   |
| `before_skill`    | Before a skill executes           |
| `after_skill`     | After a skill completes           |
| `before_tool`     | Before a tool is invoked          |
| `after_tool`      | After a tool completes            |
| `before_llm`      | Before an LLM call                |
| `after_llm`       | After an LLM call completes       |
| `before_response` | Before sending a response         |
| `after_response`  | After sending a response          |

### HookResult

```python
@dataclass
class HookResult:
    action: HookAction = HookAction.CONTINUE
    modifications: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
```

### HookMetadata

```python
@dataclass
class HookMetadata:
    name: str
    description: str
    lifecycle_event: LifecycleEvent
    priority: int = 0        # lower = runs first
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
```

### BaseHook (ABC)

```python
class BaseHook(ABC):
    def __init__(self, metadata: HookMetadata) -> None: ...
    @property
    def metadata(self) -> HookMetadata: ...
    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> HookResult: ...
```

## Hook Registry

The `HookRegistry` manages hook registration and lookup:

- `register(hook)` — add a hook
- `get(hook_id)` — retrieve by name
- `list_all()` — all registered hooks
- `list_enabled()` — only enabled hooks
- `get_for_event(event)` — enabled hooks for a lifecycle event
- `remove(hook_id)` — remove a hook
- `clear()` — remove all hooks

Hooks are automatically grouped by their `lifecycle_event` for efficient lookup.

## Hook Executor

The `HookExecutor` runs hooks for a given lifecycle event in **priority order**
(lowest priority value first). Key behaviors:

- **Terminal actions** (`BLOCK`, `APPROVAL_REQUIRED`) immediately stop the pipeline
- **MODIFY** actions accumulate via `deep_merge` across all hooks
- **RETRY** is captured but does not halt; later hooks may override
- **Exceptions** in any hook result in a `BLOCK` with the error message
- If no hooks are registered, returns `CONTINUE`

### deep_merge

Nested dictionaries are merged recursively. Scalar values from later hooks
override earlier ones. The original dictionaries are never mutated.

## Hook Manager

The `HookManager` is the top-level API. It owns the `HookRegistry` and
`HookExecutor` and provides:

```python
async def run_pipeline(event, context=None) -> HookResult
```

It logs significant pipeline results (BLOCK, APPROVAL_REQUIRED, RETRY, MODIFY).

## Built-in Hooks

| Hook                  | Lifecycle       | Priority | Action              | Purpose                                |
|-----------------------|-----------------|----------|---------------------|----------------------------------------|
| `RequestValidationHook` | `before_request` | -100     | BLOCK on injection  | Blocks SQL injection patterns          |
| `SecurityHook`          | `before_request` | -90      | BLOCK on XSS/traversal | Blocks XSS and path traversal      |
| `ToolPermissionHook`    | `before_tool`    | -50      | CONTINUE/BLOCK      | Enforces tool allowlist                |
| `HumanApprovalHook`     | `before_tool`    | -10      | APPROVAL_REQUIRED   | Pauses for high-risk tools             |
| `OutputValidationHook`  | `after_response` | -30      | MODIFY/BLOCK        | Truncates oversized output, blocks sensitive data |
| `LoggingHook` (×12)     | All events       | 100      | CONTINUE            | Logs execution at every lifecycle point|

### RequestValidationHook

Validates incoming requests:
- Detects SQL injection patterns (`SELECT...FROM`, `DROP`, `DELETE`, `INSERT`, `UNION SELECT`)
- Validates `Content-Type` header
- Returns `BLOCK` with a descriptive reason on violation

### SecurityHook

Scans for security threats:
- XSS: detects `<script>...</script>` patterns
- Path traversal: detects `../`, `..\\`, URL-encoded variants
- Checks both payload body and query parameters

### ToolPermissionHook

Enforces tool access policy:
- **Denied tools** (always blocked): `shell_execution`, `network_scan`
- **Allowed tools**: `web_search`, `python_executor`, `file_reader`
- Unknown tools are blocked
- Adds `tool_allowed: true` to context on success

### HumanApprovalHook

Requires human approval for high-risk tools:
- **`python_executor`** triggers `APPROVAL_REQUIRED`
- Attaches tool name, reasoning, and inputs to the approval request
- All other tools pass through with `CONTINUE`

### OutputValidationHook

Validates tool/skill output:
- Outputs larger than 1,000,000 characters are truncated with a `MODIFY` action
- If `sensitive_patterns` are provided in context, blocks output containing matches

### LoggingHook

One instance per lifecycle event. Logs execution duration and context keys
at `DEBUG` level. Always returns `CONTINUE`.

## Deterministic Priority Ordering

Hooks run in strict priority order (lowest number first):

1. `RequestValidationHook` (-100)
2. `SecurityHook` (-90)
3. `ToolPermissionHook` (-50)
4. `OutputValidationHook` (-30) — after_response only
5. `HumanApprovalHook` (-10)
6. Concrete hooks (0-99)
7. `LoggingHook` (100)

Hooks at the same priority run in registration order (insertion-ordered).

## Enable / Disable

Hooks can be enabled or disabled at runtime via `hook.metadata.enabled`.
Disabled hooks are excluded from `get_for_event()` and `list_enabled()`.

```python
hook = manager.registry.get("request_validation")
hook.metadata.enabled = False
```

## Testing

The hook system includes tests for:
- **Ordering**: hooks execute in priority order
- **Blocking**: `BLOCK` halts the pipeline immediately
- **Modification**: `MODIFY` accumulates via deep_merge across hooks
- **Retry**: `RETRY` is captured as the final action
- **Approval Required**: `APPROVAL_REQUIRED` halts the pipeline
- **Exception handling**: hook exceptions become BLOCK
- **No hooks**: pipeline returns CONTINUE with reason
- **All concrete hooks**: each hook's execute method with suitable inputs
