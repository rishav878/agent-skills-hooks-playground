# Implementation Plan — Agent Skills & Hooks Playground

**Date:** 2026-07-27
**Status:** Consolidated Blueprint (post-user-spec alignment)
**Total Phases:** 17

---

## A. Design Decisions

### A1. SkillSelector: LLM-driven vs rule-based

**Decision: Hybrid with LLM-first, rule-based fallback.**

The SkillSelector first calls the LLM with the user's task + available skill descriptions (+ their hook/tool metadata). The LLM returns a ranked list of skill names with confidence scores. If the top score is below 0.4 or the LLM call fails, fall back to a keyword + embedding similarity matcher (via the Embedding Provider).

### A2. LangGraph graph topology and state schema

**Decision: Single flat graph with conditional edges + typed `AgentState`.**

```python
class AgentState(TypedDict):
    messages: list[BaseMessage]       # Conversation history
    run_id: str                       # Unique run ID
    trace_id: str                     # Trace ID for observability
    current_skill: str | None         # Currently selected skill name
    skill_input: dict | None          # Skill input payload
    skill_output: dict | None         # Skill output payload
    hook_results: dict[str, Any]      # Hook execution results keyed by hook_id
    pending_approval: bool            # True when waiting for human approval
    approval_token: str | None        # Token linking to approval record
    errors: list[dict]                # Error stack
    retry_count: int                  # Current retry attempt number
```

Nodes: `initialize_run` → `classify_request` → `select_skill` → `before_skill_hooks` → `execute_skill` → `tool_router` → `before_tool_hooks` → `permission_check` → `approval_check` → `execute_tool` → `after_tool_hooks` → `validate_result` → `retry_or_continue` → `after_skill_hooks` → `generate_response` → `persist_run`.

Conditional edges: error handling, retry loops, approval pause, block signals.

### A3. Hook MODIFY propagation semantics

**Decision: Deep copy on entry, immutable result per hook.**

Each hook receives a deep copy of the context. Hook results are collected into a list. The HookExecutor composes them: successive `MODIFY` payloads are merged via `deep_merge` (dict merge with nested overwrite). `BLOCK` and `APPROVAL_REQUIRED` are terminal — no further hooks in the pipeline run.

### A4. APPROVAL_REQUIRED pause/resume mechanism

**Decision: Database-backed pause with WebSocket notification.**

When a hook returns `APPROVAL_REQUIRED`:
1. The graph node saves the current `AgentState` snapshot + approval metadata to the `ApprovalRequest` table (status = `pending`).
2. The graph returns a special `Paused` result to the API layer.
3. The API sends a WebSocket message to the frontend (`event_type: "approval_required"`) with `approval_token`, skill name, input summary, and asker.
4. The API exposes `POST /api/v1/runs/{run_id}/approve` and `POST /api/v1/runs/{run_id}/cancel`.
5. When approved/cancelled, the API updates the DB record and pushes an `approval_granted` or `approval_denied` event over WebSocket.
6. The resume mechanism re-injects the saved state into a new LangGraph run.

### A5. Multiple hook composition / conflict resolution

**Decision: Priority-ordered pipeline with terminal actions.**

Each hook declares a `priority` (integer, lower = runs first). The HookExecutor sorts by priority. If any hook returns `BLOCK`, the pipeline stops. If any hook returns `APPROVAL_REQUIRED`, the pipeline stops and enters pause. `MODIFY` payloads are merged with `deep_merge`. `CONTINUE` is the default.

### A6. Python sandbox technology

**Decision: `subprocess` with `resource` limits + JSON I/O, no `exec()`.**

Sandboxed script at a fixed path. Communication via stdin/stdout JSON. Killed after 30s timeout. Memory limited via `resource` (POSIX) or `job` objects (Windows). Blocked imports: `os`, `sys`, `subprocess`, `shutil`, `ctypes`, `socket`. Documented as **not fully secure** — production needs gVisor or Firecracker. Flagged as "HIGH RISK" in UI.

### A7. Event schema

**Decision: Past-tense descriptive event types.** See Section F.

### A8. WebSocket protocol

**Decision: Path at `/ws/runs/{run_id}`, unidirectional event stream, heartbeat every 15s.** See Section F.

### A9. API contract

**Decision: All prefixed with `/api/v1`. Run creation at `/api/v1/agents/run`.** See Section E.

### A10. Streamlit vs React division

**Decision: React is the primary full UI. Streamlit is a thin API client / debug console.**

React: React Flow, Recharts, TanStack Query, WebSocket traces, HITL controls.
Streamlit: separate minimal app calling same FastAPI endpoints. No runtime logic duplication.

### A11. LLM provider abstraction

**Decision: Abstract `BaseLLMProvider` wrapping LangChain integrations.**

```python
class BaseLLMProvider(ABC):
    async def generate(self, messages, tools=None, **kwargs) -> LLMResponse: ...
    async def stream(self, messages, **kwargs) -> AsyncIterator[str]: ...
```

Implementations: `OllamaProvider`, `GeminiProvider`, `OpenAIProvider` using LangChain's `BaseChatModel`.

### A12. Embedding provider abstraction

**Decision: Separate `BaseEmbeddingProvider` abstraction.**

```python
class BaseEmbeddingProvider(ABC):
    async def embed(self, text: str) -> list[float]: ...
    async def embed_many(self, texts: list[str]) -> list[list[float]]: ...
```

Implementations: `HuggingFaceEmbeddingProvider` (sentence-transformers), `OllamaEmbeddingProvider`, `OpenAIEmbeddingProvider`.

### A13. Database schema

See Section D.

### A14. Security policies

- **Rate limiting:** 100 req/min per IP (API key based). `slowapi`.
- **CORS:** `http://localhost:5173` (Vite), `http://localhost:8501` (Streamlit), production origin.
- **File uploads:** Max 10 MB, allowlist: `.txt`, `.csv`, `.json`, `.md`, `.py`, `.log`. MIME check via `magic`.
- **Path traversal:** `os.path.realpath()` + prefix check.
- **Secrets:** `.env` only. Redaction on all event/log output (regex: `sk-*`, `api_key` patterns).
- **Request size limit:** 5 MB on POST endpoints.

### A15. Authentication

**Decision: Simple API key auth for MVP.** `ApiKey` table with SHA-256 hashed key. `Authorization: Bearer <key>`. Default key printed on first startup.

### A16. LangChain integration

**Decision: Full LangChain integration as a utility library.**

Use LangChain for:
- **Chat models**: `BaseChatModel` as underlying integration layer
- **Prompt templates**: `ChatPromptTemplate` for skill instructions and system prompts
- **Output parsers**: `StructuredOutputParser` / `PydanticOutputParser`
- **Document loaders**: `TextLoader`, `CSVLoader`, `DirectoryLoader`
- **Text splitters**: `RecursiveCharacterTextSplitter`
- **Vector store**: LangChain's Chroma wrapper
- **Document chains**: `create_stuff_documents_chain` for RAG

LangGraph remains the **orchestration engine**.

### A17. SkillLoader component

**Decision: Separate `SkillLoader` for dynamic discovery.**

Handles loading skill definitions from disk, DB, or config. `SkillRegistry` focuses on runtime lookup. Separation allows: module packaging, runtime POST creation, dynamic enable/disable, version management.

### A18. Rich skill/tool/hook models

All entities have: `id` (UUID), `name`, `description`. Skills add `version`, `instructions`, `input_schema`, `output_schema`, `allowed_tools`. Tools add `risk_level` (LOW/MEDIUM/HIGH), `permissions`. Hooks add `priority`. All have `enabled`/`disabled`, `metadata`. POST creation endpoints provided.

### A19. Demo scenarios

1. **Research Task** — request hook, skill selection, research skill, web search tool, validation hook, response
2. **Data Analysis** — file upload, file reader, data analysis skill, Python execution, security hook, output validation
3. **High-Risk Tool** — tool permission hook, approval required, human approval, tool execution, post-tool hooks
4. **Failed Tool with Retry** — controlled tool failure, retry hook, retry execution, successful completion

### A20. Phase dependency resolution

Extract event schema into Phase 0. Observer injected into runtime as dependency (not hard-coded). Runtime declares `EventEmitter` protocol; observer implements it.

---

## B. Project Directory Structure

```
agent-skills-hooks-playground/
├── AGENTS.md
├── IMPLEMENTATION_PLAN.md
├── README.md
├── .env.example
├── .gitignore
│
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── events.py
│       │   ├── dependencies.py
│       │   └── redaction.py
│       │
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── run.py
│       │   ├── skill.py
│       │   ├── hook.py
│       │   ├── tool.py
│       │   └── event.py
│       │
│       ├── database/
│       │   ├── __init__.py
│       │   ├── session.py
│       │   ├── models.py
│       │   └── repository.py
│       │
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── state.py
│       │   ├── graph.py
│       │   ├── nodes.py
│       │   ├── conditions.py
│       │   └── approval.py
│       │
│       ├── skills/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── registry.py
│       │   ├── loader.py
│       │   ├── selector.py
│       │   ├── executor.py
│       │   └── skills/
│       │       ├── __init__.py
│       │       ├── research.py
│       │       ├── data_analysis.py
│       │       └── code_review.py
│       │
│       ├── hooks/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── registry.py
│       │   ├── manager.py
│       │   ├── executor.py
│       │   └── hooks/
│       │       ├── __init__.py
│       │       ├── request_validation.py
│       │       ├── security.py
│       │       ├── tool_permission.py
│       │       ├── logging.py
│       │       ├── output_validation.py
│       │       └── human_approval.py
│       │
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── registry.py
│       │   └── tools/
│       │       ├── __init__.py
│       │       ├── web_search.py
│       │       ├── python_executor.py
│       │       └── file_reader.py
│       │
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── provider.py
│       │   ├── ollama.py
│       │   ├── gemini.py
│       │   └── openai.py
│       │
│       ├── embeddings/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── provider.py
│       │   ├── huggingface.py
│       │   ├── ollama.py
│       │   └── openai.py
│       │
│       ├── memory/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   └── sliding_buffer.py
│       │
│       ├── rag/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── chroma_client.py
│       │   ├── retriever.py
│       │   └── document_processor.py
│       │
│       ├── observability/
│       │   ├── __init__.py
│       │   ├── emitter.py
│       │   ├── persistence.py
│       │   └── websocket_broadcast.py
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── router.py
│       │   ├── agents.py
│       │   ├── runs.py
│       │   ├── skills.py
│       │   ├── hooks.py
│       │   ├── tools.py
│       │   ├── approval.py
│       │   └── websocket.py
│       │
│       └── security/
│           ├── __init__.py
│           ├── rate_limit.py
│           └── api_key.py
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── tailwind.config.js
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   ├── client.ts
│       │   └── websocket.ts
│       ├── hooks/
│       │   ├── useRun.ts
│       │   ├── useWebSocket.ts
│       │   └── useApproval.ts
│       ├── store/
│       │   └── eventStore.ts
│       ├── components/
│       │   ├── Layout.tsx
│       │   ├── ChatInput.tsx
│       │   ├── ChatMessage.tsx
│       │   ├── SkillSelector.tsx
│       │   ├── SkillTimeline.tsx
│       │   ├── HookTimeline.tsx
│       │   ├── ToolExecutionCard.tsx
│       │   ├── ApprovalDialog.tsx
│       │   ├── EventTraceView.tsx
│       │   ├── AgentFlowGraph.tsx
│       │   ├── ExecutionChart.tsx
│       │   └── StatusBadge.tsx
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── Playground.tsx
│       │   ├── SkillsPage.tsx
│       │   ├── HooksPage.tsx
│       │   ├── ToolsPage.tsx
│       │   ├── RunHistory.tsx
│       │   ├── RunDetails.tsx
│       │   └── Settings.tsx
│       └── types/
│           ├── event.ts
│           ├── run.ts
│           ├── skill.ts
│           ├── hook.ts
│           ├── tool.ts
│           └── api.ts
│
├── streamlit_app/
│   ├── requirements.txt
│   ├── app.py
│   ├── api_client.py
│   └── pages/
│       ├── dashboard.py
│       ├── playground.py
│       ├── skills.py
│       ├── hooks.py
│       └── history.py
│
├── docs/
│   ├── architecture.md
│   ├── skills.md
│   ├── hooks.md
│   ├── workflow.md
│   ├── api.md
│   ├── development.md
│   └── deployment.md
│
├── scenarios/
│   ├── research_sample.csv
│   ├── code_sample.py
│   └── scenarios.py
│
└── tests/
    ├── conftest.py
    ├── unit/
    │   ├── test_events.py
    │   ├── test_hooks.py
    │   ├── test_skills.py
    │   ├── test_tools.py
    │   ├── test_selector.py
    │   ├── test_llm_providers.py
    │   ├── test_embeddings.py
    │   ├── test_state.py
    │   ├── test_redactor.py
    │   ├── test_db_models.py
    │   └── test_demo_scenarios.py
    ├── integration/
    │   ├── test_graph.py
    │   ├── test_api_agents.py
    │   ├── test_api_skills.py
    │   ├── test_api_hooks.py
    │   ├── test_websocket.py
    │   ├── test_approval_flow.py
    │   └── test_rag_pipeline.py
    └── e2e/
        ├── test_research_scenario.py
        ├── test_data_analysis_scenario.py
        ├── test_approval_scenario.py
        └── test_retry_scenario.py
```

---

## C. Phase Plan (Revised — 17 Phases)

### Phase 0: Foundation & Event Schema
**Goal:** Define pure-domain event schema first to break circular dependencies.

**Files:**
- `backend/pyproject.toml` — all Python deps (LangChain, sentence-transformers, fastapi, etc.)
- `backend/app/__init__.py`
- `backend/app/core/__init__.py`, `events.py`, `config.py`, `redaction.py`, `dependencies.py`
- `tests/conftest.py`, `tests/unit/test_events.py`

**Key classes:**
- `EventType` enum: `request_received, hook_started, hook_completed, skill_selected, skill_started, skill_completed, llm_started, llm_completed, tool_started, tool_completed, approval_required, approval_granted, approval_denied, retry_started, error, response_generated, run_completed`
- `Component` enum: `agent, skill, hook, tool, llm, api, runtime, system`
- `Status` enum: `pending, running, completed, failed, blocked, waiting_approval, approved, rejected`
- `AgentEvent(BaseModel)`, `Settings(BaseSettings)`, `SecretRedactor`

**Tested:** Event serialization, enum values, Settings load from env.

---

### Phase 1: Database Layer
**Goal:** SQLAlchemy models, Alembic migration, repository pattern.

**Files:**
- `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `versions/001_initial.py`
- `backend/app/database/__init__.py`, `session.py`, `models.py`, `repository.py`
- `backend/app/schemas/__init__.py`, `run.py`, `skill.py`, `hook.py`, `tool.py`, `event.py`
- `tests/unit/test_db_models.py`

**ORM models:** `AgentRun`, `ExecutionEvent`, `Skill`, `Hook`, `Tool`, `ApprovalRequest`, `ApiKey`

**Tested:** CRUD, event persistence, approval status transitions.

---

### Phase 2: LLM & Embedding Providers
**Goal:** Pluggable LLM and embedding providers with LangChain integration.

**Files:**
- `backend/app/llm/__init__.py`, `base.py`, `provider.py`, `ollama.py`, `gemini.py`, `openai.py`
- `backend/app/embeddings/__init__.py`, `base.py`, `provider.py`, `huggingface.py`, `ollama.py`, `openai.py`
- `tests/unit/test_llm_providers.py`, `tests/unit/test_embeddings.py`

**Key classes:**
- `BaseLLMProvider.generate()`, `.stream()`, `.from_config()` — wraps LangChain `BaseChatModel`
- `BaseEmbeddingProvider.embed()`, `.embed_many()` — wraps sentence-transformers
- `ProviderFactory.create(provider_name, config)`

**Tested:** Mock provider, factory dispatch, LangChain model integration.

---

### Phase 3: Skills Core
**Goal:** BaseSkill, SkillLoader, SkillRegistry, SkillSelector, SkillExecutor, 3 skills.

**Files:**
- `backend/app/skills/__init__.py`, `base.py`, `registry.py`, `loader.py`, `selector.py`, `executor.py`
- `skills/__init__.py`, `research.py`, `data_analysis.py`, `code_review.py`
- `tests/unit/test_skills.py`, `tests/unit/test_selector.py`

**Key classes:**
- `BaseSkill`: `id`, `name`, `description`, `version`, `instructions`, `input_schema`, `output_schema`, `allowed_tools`, `metadata`, `enabled`, `async execute()`
- `SkillLoader.load_from_db()`, `.load_from_config()`, `.discover_modules()`
- `SkillRegistry.register()`, `.get()`, `.get_by_name()`, `.list_all()`
- `SkillSelector`: hybrid LLM + embedding fallback
- `SkillExecutor`: wraps execution with hooks

**Tested:** Registration, executor dispatch, selector logic, each skill with mocked tools.

---

### Phase 4: Tools Core
**Goal:** BaseTool, ToolRegistry, sandboxed Python executor, web search, file reader.

**Files:**
- `backend/app/tools/__init__.py`, `base.py`, `registry.py`
- `tools/__init__.py`, `web_search.py`, `python_executor.py`, `file_reader.py`
- `tests/unit/test_tools.py`, `tests/unit/test_sandbox_isolation.py`

**Key classes:**
- `BaseTool`: `id`, `name`, `description`, `input_schema`, `output_schema`, `permissions`, `risk_level`
- `PythonExecutor`: subprocess sandbox, 30s timeout, restricted imports
- `WebSearchTool`: HTTP GET with provider abstraction
- `FileReader`: path traversal safe, size/extension limits

**Tested:** Sandbox isolation, path traversal rejection, timeout, web search parsing.

---

### Phase 5: Hooks Core
**Goal:** BaseHook, HookRegistry, HookManager, HookExecutor, 6 concrete hooks.

**Files:**
- `backend/app/hooks/__init__.py`, `base.py`, `registry.py`, `manager.py`, `executor.py`
- `hooks/__init__.py`, `request_validation.py`, `security.py`, `tool_permission.py`, `logging.py`, `output_validation.py`, `human_approval.py`
- `tests/unit/test_hooks.py`

**Key classes:**
- `BaseHook`: `name`, `priority`, `events: list[EventType]`, `async execute(context) -> HookResult`
- `HookResult`: `action: HookAction`, `modifications: dict`, `reason: str`
- `HookAction`: `CONTINUE, BLOCK, MODIFY, RETRY, APPROVAL_REQUIRED`
- `HookManager.run_pipeline(event_type, context)`: orchestrates priority-ordered composition

**Tested:** Pipeline ordering, terminal actions, deep_merge, APPROVAL_REQUIRED signal.

---

### Phase 6: LangGraph Agent Runtime
**Goal:** Graph topology, nodes, conditions, state management, retry loop, approval pause.

**Files:**
- `backend/app/agents/__init__.py`, `state.py`, `graph.py`, `nodes.py`, `conditions.py`, `approval.py`
- `tests/integration/test_graph.py`

**Key classes:**
- `AgentState` TypedDict
- `build_agent_graph() -> CompiledGraph` — all nodes and edges
- Nodes: `initialize_run`, `classify_request`, `select_skill`, `before_skill_hooks`, `execute_skill`, `tool_router`, `before_tool_hooks`, `permission_check`, `approval_check`, `execute_tool`, `after_tool_hooks`, `validate_result`, `retry_or_continue`, `after_skill_hooks`, `generate_response`, `persist_run`
- Conditional edges for error, retry, block, approval pause
- `ApprovalManager.pause_for_approval()`, `.resume()`
- Retry: max 3, exponential backoff

**Tested:** Graph compilation, full run with mocks, retry on failure, pause on APPROVAL_REQUIRED.

---

### Phase 7: Observability
**Goal:** EventEmitter injection, event persistence, redaction, WebSocket broadcast.

**Files:**
- `backend/app/observability/__init__.py`, `emitter.py`, `persistence.py`, `websocket_broadcast.py`
- `tests/unit/test_observability.py`, `tests/unit/test_redactor.py`

**Key classes:**
- `EventEmitter(Protocol)`: `async emit(event: AgentEvent)`
- `DatabaseEventEmitter`, `WebSocketEventEmitter`, `CompositeEventEmitter`
- Graph factory accepts emitter parameter; nodes call `emitter.emit()` at each lifecycle point

**Tested:** Event emission at each graph node, redaction, composite fan-out, DB persistence.

---

### Phase 8: FastAPI Core Endpoints
**Goal:** REST API for agents, runs, skills, hooks, tools, events, approval.

**Files:**
- `backend/app/main.py`, `api/__init__.py`, `api/router.py`
- `api/agents.py`, `api/runs.py`, `api/skills.py`, `api/hooks.py`, `api/tools.py`, `api/approval.py`
- `tests/integration/test_api_agents.py`, `test_api_skills.py`, `test_api_hooks.py`

**Key endpoints:** See Section E.

**Tested:** All endpoints with mocked runtime, background run creation, approval flow.

---

### Phase 9: WebSocket & Event Streaming
**Goal:** Real-time event push to frontend clients.

**Files:**
- `backend/app/api/websocket.py`
- `frontend/src/api/websocket.ts`

**Key features:**
- WebSocket endpoint at `ws://host/ws/runs/{run_id}`
- Connection lifecycle: authenticate -> subscribe -> stream -> cleanup
- `WebSocketEventEmitter` broadcasts to all subscribers of that `run_id`
- Frontend `useWebSocket` hook: auto-connect, exponential backoff reconnect (max 30s), heartbeat ping/pong every 15s

**Tested:** WebSocket connection, event streaming, reconnect behavior, heartbeat.

---

### Phase 10: React Frontend — Foundation
**Goal:** Project scaffolding, API client, WebSocket hook, layout, routing.

**Files:**
- `frontend/package.json`, `tsconfig.json`, `vite.config.ts`, `tailwind.config.js`, `index.html`
- `src/main.tsx`, `App.tsx`, `api/client.ts`, `api/websocket.ts`
- `hooks/useRun.ts`, `useWebSocket.ts`, `useApproval.ts`
- `store/eventStore.ts`
- `components/Layout.tsx`, `ChatInput.tsx`, `ChatMessage.tsx`, `StatusBadge.tsx`
- `pages/Dashboard.tsx`, `Playground.tsx`
- `types/event.ts`, `run.ts`, `api.ts`

**Key components:**
- `App.tsx`: React Router with all routes
- `Dashboard`: overview of system status, recent runs
- `Playground`: chat input on left, live flow on right, timeline on bottom

**Tested:** (Manual) UI renders, messages send/receive, WebSocket connects.

---

### Phase 11: React Frontend — Visualization
**Goal:** React Flow graph, timelines, Recharts, tool execution cards.

**Files:**
- `components/SkillTimeline.tsx`, `HookTimeline.tsx`, `ToolExecutionCard.tsx`
- `components/EventTraceView.tsx`, `AgentFlowGraph.tsx`, `ExecutionChart.tsx`
- `pages/SkillsPage.tsx`, `HooksPage.tsx`, `ToolsPage.tsx`, `RunHistory.tsx`, `RunDetails.tsx`
- `types/skill.ts`, `hook.ts`, `tool.ts`

**Key components:**
- `AgentFlowGraph`: React Flow graph rendering events as nodes with animated edges
- `ExecutionChart`: Recharts timeline showing step durations
- `SkillTimeline`: vertical timeline for skill lifecycle
- `HookTimeline`: shows each hook with its action result
- `RunDetails`: full event log for a single run

**Tested:** (Manual) Visual correctness with real events.

---

### Phase 12: Human-in-the-Loop (Frontend)
**Goal:** Approval dialog, pause visual state, approve/cancel buttons.

**Files:**
- `components/ApprovalDialog.tsx`

**Key components:**
- `ApprovalDialog`: modal showing skill name, input summary, asker, reason, approve/cancel buttons
- Visual state: `waiting_approval` status shows pulsing yellow border on graph node, approval dialog, chat input disabled

**Tested:** (Manual) Approval flow end-to-end.

---

### Phase 13: Memory & RAG
**Goal:** Conversation memory (sliding window + summarization) and ChromaDB-based RAG.

**Files:**
- `backend/app/memory/__init__.py`, `base.py`, `sliding_buffer.py`
- `backend/app/rag/__init__.py`, `base.py`, `chroma_client.py`, `retriever.py`, `document_processor.py`
- `tests/unit/test_memory.py`, `tests/unit/test_rag.py`, `tests/integration/test_rag_pipeline.py`

**Key classes:**
- `BaseMemory`: `async add(message)`, `async get_context()`
- `SlidingWindowMemory`: keeps last N messages, summarizes older ones via LLM
- `ChromaClient`: wraps chromadb, LangChain Chroma integration
- `DocumentProcessor`: LangChain loaders + `RecursiveCharacterTextSplitter`
- `Retriever`: `async retrieve(query, top_k) -> list[Document]`

**Tested:** Memory buffer trimming, summary generation, ChromaDB add/search, RAG context injection.

---

### Phase 14: Demo Scenarios
**Goal:** 4 seeded demo scenarios for end-to-end testing and demonstration.

**Files:**
- `scenarios/scenarios.py` — scenario definitions
- `scenarios/research_sample.csv`, `scenarios/code_sample.py`
- `tests/e2e/test_research_scenario.py`, `test_data_analysis_scenario.py`, `test_approval_scenario.py`, `test_retry_scenario.py`

**Key features:**
- Seed data files for research and data analysis demos
- Each scenario specifies expected events, skills, hooks, and tools
- E2E tests validate complete flow from input to output

**Tested:** Full e2e tests for all 4 scenarios.

---

### Phase 15: Security Hardening
**Goal:** Rate limiting, CORS hardening, upload validation, API key auth, secret redaction audit.

**Files:**
- `backend/app/security/__init__.py`, `rate_limit.py`, `api_key.py`
- Modifications to existing files for middleware registration

**Tested:** Rate limit triggers, invalid API key returns 401, malicious upload path returns 400, redactor catches all patterns.

---

### Phase 16: Documentation
**Goal:** All docs files, README update, architecture documentation.

**Files:**
- `docs/architecture.md`, `docs/skills.md`, `docs/hooks.md`, `docs/workflow.md`, `docs/api.md`, `docs/development.md`, `docs/deployment.md`
- `README.md` update

**Key content:**
- Architecture: system overview, component diagram, data flow
- Skills: definition, base class, registration, selection, execution
- Hooks: lifecycle points, hook interface, composition, actions
- Workflow: LangGraph graph, nodes, edges, conditional routing
- API: all endpoints, request/response schemas, examples
- Development: setup, configuration, testing, contribution guide
- Deployment: Docker, docker-compose, environment variables, CI/CD

---

### Phase 17: Docker, CI/CD & Final Audit
**Goal:** Dockerfiles, docker-compose, CI workflow, final test pass.

**Files:**
- `Dockerfile.backend`, `Dockerfile.frontend`
- `docker-compose.yml` (backend, frontend, chromadb)
- `.github/workflows/ci.yml`

**Key actions:**
- Docker multi-stage builds for backend and frontend
- docker-compose with volumes for SQLite and ChromaDB
- CI: lint (ruff), type-check (mypy), unit tests, integration tests, e2e tests
- Final audit: verify all AGENTS.md and user spec principles are satisfied

**Tested:** `docker-compose up` launches everything, `pytest` passes in CI, frontend connects to backend.

---

## D. Database Schema

### Table: `agent_runs`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK | |
| `status` | `VARCHAR(32)` | NOT NULL, default `'pending'` | pending, running, completed, failed, blocked, waiting_approval |
| `input` | `TEXT` | NOT NULL | JSON |
| `output` | `TEXT` | | JSON |
| `selected_skill` | `VARCHAR(128)` | | |
| `error` | `TEXT` | | JSON |
| `retry_count` | `INTEGER` | NOT NULL, default 0 | |
| `trace_id` | `VARCHAR(64)` | NOT NULL | |
| `created_at` | `TIMESTAMP` | NOT NULL | |
| `updated_at` | `TIMESTAMP` | NOT NULL | |

**Indexes:** `idx_runs_status`, `idx_runs_created_at`.

### Table: `execution_events`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK | |
| `run_id` | `UUID` | FK -> agent_runs(id), NOT NULL | |
| `trace_id` | `VARCHAR(64)` | NOT NULL | |
| `event_type` | `VARCHAR(32)` | NOT NULL | See EventType enum |
| `component` | `VARCHAR(32)` | NOT NULL | See Component enum |
| `status` | `VARCHAR(24)` | NOT NULL | See Status enum |
| `timestamp` | `TIMESTAMP` | NOT NULL | |
| `duration_ms` | `INTEGER` | | |
| `input` | `TEXT` | | Redacted JSON |
| `output` | `TEXT` | | Redacted JSON |
| `error` | `TEXT` | | JSON |
| `metadata` | `TEXT` | | JSON |

**Indexes:** `idx_events_run_id`, `idx_events_type`, `idx_events_ts`.

### Table: `skills`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK | |
| `name` | `VARCHAR(128)` | NOT NULL, UNIQUE | |
| `description` | `TEXT` | NOT NULL | |
| `version` | `VARCHAR(32)` | NOT NULL | |
| `instructions` | `TEXT` | NOT NULL | System prompt for the skill |
| `input_schema` | `TEXT` | | JSON Schema |
| `output_schema` | `TEXT` | | JSON Schema |
| `allowed_tools` | `TEXT` | | JSON array of tool names |
| `metadata` | `TEXT` | | JSON |
| `enabled` | `BOOLEAN` | NOT NULL, default true | |
| `created_at` | `TIMESTAMP` | NOT NULL | |
| `updated_at` | `TIMESTAMP` | NOT NULL | |

### Table: `hooks`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK | |
| `name` | `VARCHAR(128)` | NOT NULL, UNIQUE | |
| `description` | `TEXT` | | |
| `lifecycle_event` | `VARCHAR(32)` | NOT NULL | Which event this hook targets |
| `priority` | `INTEGER` | NOT NULL, default 0 | Lower runs first |
| `enabled` | `BOOLEAN` | NOT NULL, default true | |
| `metadata` | `TEXT` | | JSON |
| `created_at` | `TIMESTAMP` | NOT NULL | |

### Table: `tools`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK | |
| `name` | `VARCHAR(128)` | NOT NULL, UNIQUE | |
| `description` | `TEXT` | NOT NULL | |
| `input_schema` | `TEXT` | | JSON Schema |
| `output_schema` | `TEXT` | | JSON Schema |
| `risk_level` | `VARCHAR(16)` | NOT NULL, default `'medium'` | low, medium, high |
| `permissions` | `TEXT` | | JSON |
| `enabled` | `BOOLEAN` | NOT NULL, default true | |
| `created_at` | `TIMESTAMP` | NOT NULL | |

### Table: `approval_requests`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK | |
| `run_id` | `UUID` | FK -> agent_runs(id), NOT NULL | |
| `skill_name` | `VARCHAR(128)` | NOT NULL | |
| `input_summary` | `TEXT` | NOT NULL | |
| `asker` | `VARCHAR(64)` | NOT NULL | Hook that requested approval |
| `reason` | `TEXT` | | |
| `status` | `VARCHAR(16)` | NOT NULL, default `'pending'` | pending, approved, cancelled |
| `state_snapshot` | `TEXT` | NOT NULL | JSON of AgentState |
| `created_at` | `TIMESTAMP` | NOT NULL | |
| `decided_at` | `TIMESTAMP` | | |

**Indexes:** `idx_approval_run`, `idx_approval_status`.

### Table: `api_keys`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | PK | |
| `key_hash` | `VARCHAR(128)` | NOT NULL, UNIQUE | SHA-256 of key |
| `label` | `VARCHAR(128)` | | |
| `enabled` | `BOOLEAN` | NOT NULL, default true | |
| `created_at` | `TIMESTAMP` | NOT NULL | |

---

## E. API Contract

All endpoints prefixed with `/api/v1`. All request/response bodies are JSON.

### Agents

| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| `POST` | `/api/v1/agents/run` | `{ "input": string, "skill": string \| null }` | `{ "run_id": uuid, "status": "pending" }` | Creates run, starts graph in background |
| `GET` | `/api/v1/agents` | | `{ "agents": AgentSummary[] }` | List available agents (single agent for MVP) |

### Runs

| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| `GET` | `/api/v1/runs` | Query: `status?`, `limit?`, `offset?` | `{ "runs": RunSummary[], "total": int }` | List runs |
| `GET` | `/api/v1/runs/{run_id}` | | `RunDetail` | Full run with current state |
| `GET` | `/api/v1/runs/{run_id}/events` | Query: `event_type?`, `component?`, `limit?`, `offset?` | `{ "events": AgentEvent[], "total": int }` | Events for a run |
| `POST` | `/api/v1/runs/{run_id}/approve` | `{ "approval_token": string, "modified_input": dict \| null }` | `{ "status": "approved" }` | Approve pending action |
| `POST` | `/api/v1/runs/{run_id}/cancel` | `{ "approval_token": string, "reason": string \| null }` | `{ "status": "cancelled" }` | Cancel pending action |

### Skills

| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| `GET` | `/api/v1/skills` | | `{ "skills": SkillDef[] }` | List registered skills |
| `GET` | `/api/v1/skills/{skill_id}` | | `SkillDef` | Get skill detail |
| `POST` | `/api/v1/skills` | `SkillCreate` | `SkillDef` | Register new skill at runtime |

### Hooks

| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| `GET` | `/api/v1/hooks` | | `{ "hooks": HookDef[] }` | List registered hooks |
| `GET` | `/api/v1/hooks/{hook_id}` | | `HookDef` | Get hook detail |
| `POST` | `/api/v1/hooks` | `HookCreate` | `HookDef` | Register new hook at runtime |

### Tools

| Method | Path | Request | Response | Notes |
|--------|------|---------|----------|-------|
| `GET` | `/api/v1/tools` | | `{ "tools": ToolDef[] }` | List registered tools |

### WebSocket

| Path | Notes |
|------|-------|
| `ws://host/ws/runs/{run_id}?token={api_key}` | Streams AgentEvent JSON messages for the run |

### Health

| Method | Path | Response |
|--------|------|----------|
| `GET` | `/api/v1/health` | `{ "status": "ok", "version": "0.1.0" }` |

---

## F. Event Schema & WebSocket Protocol

### F1. EventType Enum

```python
class EventType(str, Enum):
    request_received = "request_received"
    hook_started = "hook_started"
    hook_completed = "hook_completed"
    skill_selected = "skill_selected"
    skill_started = "skill_started"
    skill_completed = "skill_completed"
    llm_started = "llm_started"
    llm_completed = "llm_completed"
    tool_started = "tool_started"
    tool_completed = "tool_completed"
    approval_required = "approval_required"
    approval_granted = "approval_granted"
    approval_denied = "approval_denied"
    retry_started = "retry_started"
    error = "error"
    response_generated = "response_generated"
    run_completed = "run_completed"
```

### F2. Component Enum

```python
class Component(str, Enum):
    agent = "agent"
    skill = "skill"
    hook = "hook"
    tool = "tool"
    llm = "llm"
    api = "api"
    runtime = "runtime"
    system = "system"
```

### F3. Status Enum

```python
class Status(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    blocked = "blocked"
    waiting_approval = "waiting_approval"
    approved = "approved"
    rejected = "rejected"
```

### F4. AgentEvent Pydantic Model

```python
class AgentEvent(BaseModel):
    event_id: str                          # UUID
    run_id: str                            # UUID
    trace_id: str                          # UUID
    timestamp: datetime                    # ISO 8601 UTC
    event_type: EventType
    component: Component
    status: Status
    duration_ms: int | None = None         # Set after completion
    input: dict | None = None              # May be redacted
    output: dict | None = None             # May be redacted
    error: dict | None = None              # Only on failure
    metadata: dict = Field(default_factory=dict)
```

### F5. WebSocket Message Format

**Direction:** Server -> Client (unidirectional for MVP).

**Server -> Client:**
```json
{ "type": "event", "payload": { /* AgentEvent as JSON */ } }
```

**Client -> Server:**
```json
{ "type": "ping" }
```

**Connection lifecycle:**
1. Client opens `ws://host/ws/runs/{run_id}?token={api_key}`
2. Server validates API key, creates subscription for `run_id`
3. Server sends replay of last 100 events:
   ```json
   { "type": "replay", "payload": { "events": [AgentEvent, ...] } }
   ```
4. Server streams live events as they occur
5. Server sends heartbeat every 15s:
   ```json
   { "type": "heartbeat" }
   ```
6. Client sends `{ "type": "ping" }` as keepalive (optional)
7. On disconnect: client exponential backoff reconnect (1s, 2s, 4s, 8s, 16s, max 30s), up to 10 attempts. Server cleans up after 60s timeout.

---

## G. Testing Strategy

### Framework
- **Pytest** (Python), **vitest** (TypeScript React)
- Coverage: `pytest-cov` target 85% backend, 70% frontend
- Frontend: `@testing-library/react`, `msw` for API mocks

### Per-Phase Testing

| Phase | Tests | Type | Target |
|-------|-------|------|--------|
| 0 | Event serialization, enum integrity | unit | 95% |
| 1 | CRUD on all tables, status transitions, migration | unit | 90% |
| 2 | Mock provider, factory dispatch, LangChain model integration | unit | 95% |
| 3 | Skill registration, executor, selector logic | unit | 90% |
| 4 | Sandbox isolation, path traversal, timeout | unit | 90% |
| 5 | Hook pipeline, terminal action, deep_merge | unit | 95% |
| 6 | Graph compilation, full run, retry, pause, routing | integration | 85% |
| 7 | Event emission, redaction, composite emitter | unit + integration | 90% |
| 8 | All endpoints, background run, approval flow | integration | 85% |
| 9 | WebSocket connect, streaming, reconnect | integration | 85% |
| 10-12 | (Manual) UI scaffolding, visual, approval | manual | n/a |
| 13 | Memory buffer, ChromaDB, RAG context | unit + integration | 85% |
| 14 | 4 scenario e2e flows | e2e | 90% |
| 15 | Rate limit, auth, upload validation | unit + integration | 95% |
| 16 | Doc accuracy review | manual | n/a |
| 17 | Docker compose, CI pipeline | e2e | 80% |

### Key Fixtures
- `test_db`: in-memory SQLite with `create_all`
- `mock_llm_provider`: predefined responses
- `mock_tool_registry`, `mock_hook_registry`
- `event_collector`: in-memory accumulator
- `test_client`: FastAPI `TestClient`

### Success Criteria
- `pytest tests/` — all pass
- `coverage report` — >= 85%
- No `exec()`/`eval()` in production code
- No hard-coded API keys
- Every LangGraph node emits at least one event

---

## H. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|------------|--------|------------|
| 1 | LangGraph state corruption under concurrent runs | Medium | High | TypedDict (immutable), unique run_id, LangGraph Checkpoint per thread, 10 concurrent run test |
| 2 | Python sandbox escape | Low | Critical | AST import restriction, 30s timeout, 256MB limit, documented as not fully secure, opt-in flag |
| 3 | WebSocket connection storms | Medium | Medium | 5 concurrent WS per IP, 60s cleanup, frontend backoff |
| 4 | LLM provider API changes/outages | Medium | High | Provider abstraction via env var, circuit breaker (3 failures -> fallback 60s), clear error messages |
| 5 | Hook MODIFY merge conflicts | Medium | Medium | deep_merge with last-writer-wins, debug logging, hook authoring guide: "prefer unique top-level keys" |
| 6 | LangChain version conflicts with LangGraph | Low | Medium | Pin compatible versions in pyproject.toml, CI dependency resolution check |
| 7 | Embedding model download size (Hugging Face) | Medium | Low | Cache models, allow offline mode, fall back to Ollama embeddings if no HF model |

---

## I. Demo Scenarios Detail

### Scenario 1: Research Task
**Input:** "Research the latest AI agent frameworks in 2026."
**Expected flow:**
1. `request_received` event
2. `hook_started` + `hook_completed` (request validation -> CONTINUE)
3. `skill_selected` -> Research skill
4. `hook_started` + `hook_completed` (security -> CONTINUE)
5. `skill_started` + `skill_completed`
6. `tool_started` + `tool_completed` (web search -> results)
7. `hook_started` + `hook_completed` (output validation -> MODIFY)
8. `response_generated` -> structured summary with citations
9. `run_completed`

### Scenario 2: Data Analysis
**Input:** Upload CSV, ask "Analyze this data and find trends."
**Expected flow:**
1. File read via FileReader tool
2. DataAnalysis skill selected
3. Security hook validates CSV content
4. PythonExecutor runs analysis code (safe sandbox)
5. Output validation hook checks result structure
6. Response includes statistics, charts data, insights

### Scenario 3: High-Risk Tool Approval
**Input:** "Run this Python script to process my data."
**Expected flow:**
1. Tool selected: PythonExecutor (HIGH risk)
2. ToolPermissionHook fires -> APPROVAL_REQUIRED
3. `approval_required` event to UI
4. User approves via dialog
5. `approval_granted` event
6. Python tool executes
7. Results returned

### Scenario 4: Retry on Failure
**Input:** A task that triggers a controlled tool failure.
**Expected flow:**
1. Tool executes and fails
2. `retry_started` event
3. Retry with exponential backoff
4. Second attempt succeeds
5. `tool_completed` with success status

---

## J. Success Criteria Checklist

- [ ] User can submit a task via `POST /api/v1/agents/run`
- [ ] Agent selects a real skill via SkillSelector (LLM + embedding)
- [ ] Skills execute through SkillRegistry + SkillExecutor
- [ ] Hooks execute through HookManager in priority order
- [ ] Tools execute through ToolRegistry with permission checks
- [ ] LangGraph controls all workflow execution
- [ ] 17 event types are emitted from actual execution
- [ ] Events persisted in `execution_events` table
- [ ] Events stream to UI via WebSocket at `/ws/runs/{run_id}`
- [ ] React Flow displays actual execution state in real time
- [ ] Human approval works end-to-end (hook -> dialog -> approve -> resume)
- [ ] Retry logic works (max 3, exponential backoff)
- [ ] Skills inspectable via `GET /api/v1/skills`
- [ ] Hooks inspectable via `GET /api/v1/hooks`
- [ ] Runs inspectable via `GET /api/v1/runs/{run_id}`
- [ ] Streamlit works as an API client (read-only)
- [ ] React works as the primary UI with all 8 pages
- [ ] 4 demo scenarios run correctly as e2e tests
- [ ] Docker setup works with docker-compose
- [ ] All 7 docs files written and accurate
- [ ] Backend test coverage >= 85%
- [ ] No hard-coded secrets, no exec()/eval(), no fake events
