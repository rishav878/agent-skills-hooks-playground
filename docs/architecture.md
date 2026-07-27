# Architecture

## System Overview

The Agent Skills & Hooks Playground is a production-quality interactive platform
for understanding, demonstrating, and visualizing how modern AI agents work internally.

## Core Concepts

### Agent
The agent is responsible for reasoning, decision-making, routing, and orchestration.
Execution is managed by a LangGraph workflow with typed state and conditional routing.

### Skill
A skill represents WHAT an agent can do. Skills are registered in a SkillRegistry,
selected by a SkillSelector, and executed by a SkillExecutor. All skill execution
passes through the Hook Manager.

### Hook
A hook represents WHEN lifecycle logic executes. Hooks intercept execution at
defined lifecycle points (before_request, after_skill, before_tool, etc.) and
can CONTINUE, BLOCK, MODIFY, RETRY, or request APPROVAL.

### Tool
A tool performs an external operation. Tools are registered in a ToolRegistry
with metadata including risk level, input schema, and permissions.

## Architecture Diagram

```
User
  |
  v
FastAPI (REST + WebSocket)
  |
  v
LangGraph Agent Runtime
  |
  +-- Skill Selector --> SkillRegistry --> Skill Executor
  |                           |
  +-- Hook Manager  --> HookRegistry --> Hook Executor
  |                           |
  +-- Tool Router   --> ToolRegistry --> Tool Executor
  |
  v
Observability (EventEmitter)
  |
  +-- Database (event persistence)
  +-- WebSocket (real-time streaming)
  |
  v
React UI (React Flow, Recharts, TanStack Query)
Streamlit UI (thin API client)
```

## Technology Stack

- **Backend:** Python 3.12+, FastAPI, Pydantic v2, LangGraph, SQLAlchemy 2.x
- **LLM Providers:** Ollama, Google Gemini, OpenAI (via LangChain integration)
- **Vector Store:** ChromaDB
- **Frontend:** React, TypeScript, Vite, React Flow, Tailwind CSS, TanStack Query, Recharts
- **Infrastructure:** Docker, Docker Compose, GitHub Actions CI

## Project Structure

```
backend/
  app/
    core/          - Configuration, event schema, redaction
    schemas/       - Pydantic API request/response models
    database/      - SQLAlchemy models, session, repository
    agents/        - LangGraph runtime, state, graph nodes
    skills/        - Skill system (base, registry, loader, selector, executor)
    hooks/         - Hook system (base, registry, manager, executor)
    tools/         - Tool system (base, registry, implementations)
    llm/           - LLM provider abstraction (Ollama, Gemini, OpenAI)
    embeddings/    - Embedding provider abstraction (HuggingFace, Ollama, OpenAI)
    memory/        - Conversation memory (sliding window)
    rag/           - RAG pipeline (ChromaDB, retrieval, document processing)
    observability/ - Event emitter, persistence, WebSocket broadcast
    api/           - FastAPI route handlers
    security/      - Rate limiting, API key auth

frontend/          - React + TypeScript + Vite

streamlit_app/     - Minimal Streamlit API client

docs/              - Architecture, API, development, deployment docs
```

## Data Flow

1. User submits a task via `POST /api/v1/agents/run`
2. FastAPI creates a run, generates trace_id, starts LangGraph in background
3. LangGraph executes nodes: initialize -> classify -> select skill -> hooks -> execute -> tools -> hooks -> respond
4. Each node emits structured events via EventEmitter
5. Events are persisted to the database and streamed via WebSocket
6. React UI renders events in real time using React Flow and timelines
7. On approval_required, the graph pauses and waits for user input
8. User approves/cancels via API, graph resumes from saved state

## LangGraph Execution Flow

```
START
  |
  v
initialize_run
  |
  v
before_request_hooks  <-- RequestValidationHook, SecurityHook, LoggingHook
  |
  v
classify_request  <-- SkillSelector (LLM -> Embedding -> Keyword)
  |
  v
before_skill_hooks <-- LoggingHook
  |
  v
execute_skill  <-- ResearchSkill / DataAnalysisSkill / CodeReviewSkill
  |
  v
tool_router  <-- conditional: needs tool? -> before_tool_hooks | no tool -> after_skill_hooks
  |
  v
before_tool_hooks  <-- HumanApprovalHook (python_executor), ToolPermissionHook, LoggingHook
  |
  v
permission_check  <-- checks DENY permissions
  |
  v
approval_check  <-- needs approval? -> pause_for_approval | approved -> execute_tool
  |
  +-- pause_for_approval --> persists ApprovalRequest --> END
  |
  v
execute_tool  <-- WebSearchTool / PythonExecutionTool / FileReaderTool
  |
  v
after_tool_hooks --> validate_result --> retry_or_continue
  |
  v
after_skill_hooks --> generate_response --> before_response_hooks
  |
  v
after_request_hooks --> persist_run --> END
```

On resume after approval, all nodes before `permission_check` are skipped
via the `resumed=True` flag, and execution continues from `approval_check`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/health | Health check |
| POST | /api/v1/agents/run | Execute an agent task |
| GET | /api/v1/skills | List registered skills |
| GET | /api/v1/skills/{id} | Get skill details |
| GET | /api/v1/hooks | List registered hooks |
| GET | /api/v1/hooks/{id} | Get hook details |
| GET | /api/v1/tools | List registered tools |
| GET | /api/v1/tools/{id} | Get tool details |
| GET | /api/v1/runs | List all runs |
| GET | /api/v1/runs/{id} | Get run details |
| GET | /api/v1/runs/{id}/events | Get run events |
| WS | /api/v1/runs/ws/{run_id} | WebSocket event stream |
| POST | /api/v1/runs/{run_id}/approve | Approve a pending request |
| POST | /api/v1/runs/{run_id}/cancel | Cancel a pending request |
