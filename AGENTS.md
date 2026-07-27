# AGENTS.md

# Agent Skills & Hooks Playground

## Project Purpose

This project is a production-quality interactive platform for demonstrating
and visualizing the real execution lifecycle of AI agents.

The system must demonstrate:

- Agents
- Skills
- Hooks
- Tools
- LangGraph workflows
- Conditional routing
- Retries
- Human-in-the-loop
- Memory
- RAG
- Observability
- Real-time execution tracing

The UI must visualize the REAL agent runtime.

Never simulate execution events in the production UI.

---

# Core Architectural Principles

## 1. Skills

A Skill represents WHAT an agent can do.

Skills must be implemented through:

- BaseSkill
- SkillRegistry
- SkillSelector
- SkillExecutor

Initial skills:

- Research
- Data Analysis
- Code Review

Skills must not bypass the Hook Manager.

---

## 2. Hooks

Hooks represent WHEN lifecycle logic executes.

Hooks must be managed centrally through:

- BaseHook
- HookRegistry
- HookManager
- HookExecutor

Supported lifecycle events include:

- before_request
- after_request
- before_agent
- after_agent
- before_skill
- after_skill
- before_tool
- after_tool
- before_llm
- after_llm
- before_response
- after_response

Supported actions:

- CONTINUE
- BLOCK
- MODIFY
- RETRY
- APPROVAL_REQUIRED

---

## 3. Tools

Tools represent external capabilities.

Tools must be registered through a Tool Registry.

Initial tools:

- Web Search
- Python Execution
- File Reader

Python execution is HIGH risk.

Never allow unrestricted shell execution.

Never expose environment secrets to tools.

---

## 4. Agent Runtime

LangGraph is the orchestration engine.

The agent runtime must support:

- State management
- Conditional routing
- Skill selection
- Tool execution
- Retry loops
- Error handling
- Human approval
- Persistence

Avoid global mutable state.

Concurrent agent runs must remain isolated.

---

## 5. Observability

Every meaningful execution step must emit structured events.

Events must come from the actual runtime.

Never create fake events for the production UI.

Events must contain:

- event_id
- run_id
- trace_id
- timestamp
- event_type
- component
- status
- duration
- input/output where safe
- error
- metadata

Sensitive information must be redacted.

---

## 6. Frontend

The React UI must visualize actual backend execution.

Use:

- React
- TypeScript
- React Flow
- Tailwind CSS
- TanStack Query
- WebSockets

The Streamlit UI is an API client.

Do not duplicate agent runtime logic inside Streamlit.

---

## 7. Backend

Use:

- Python 3.12+
- FastAPI
- Pydantic v2
- LangGraph
- SQLAlchemy
- Alembic

Use service layers and Pydantic API schemas.

Do not expose database models directly through APIs.

---

## 8. LLM Providers

Use an LLM provider abstraction.

Support:

- Ollama
- Google Gemini
- OpenAI-compatible providers

Do not hard-code a provider.

Do not hard-code API keys.

Use environment variables.

The coding model used by the coding agent is separate from
the LLM used by the application runtime.

---

## 9. Database

Use:

- PostgreSQL for production
- SQLite only for local development if appropriate
- ChromaDB for vector storage

Use Alembic migrations.

---

## 10. Security

Always consider:

- Input validation
- Prompt injection
- Tool permissions
- Python execution risks
- File upload validation
- Path traversal
- Secret redaction
- CORS
- Rate limiting
- Request size limits

Never claim arbitrary Python execution is fully secure without sandboxing.

---

# Development Rules

Before implementing a new major feature:

1. Inspect the existing architecture.
2. Understand existing modules.
3. Do not unnecessarily rewrite working code.
4. Preserve existing interfaces unless there is a strong reason to change them.
5. Add tests for new functionality.
6. Update documentation.
7. Run tests after implementation.
8. Report failures honestly.

Do not:

- Create fake implementations and present them as complete.
- Use hard-coded API keys.
- Put all logic in main.py.
- Put all logic in LangGraph nodes.
- Duplicate runtime logic in Streamlit.
- Create unnecessary microservices.
- Add Kubernetes unless explicitly requested.
- Silently skip requirements.

---

# Implementation Process

The project must be implemented incrementally.

Recommended order:

1. Architecture planning
2. Foundation
3. Skills
4. Hooks
5. Tools
6. LangGraph runtime
7. Observability
8. FastAPI
9. Streamlit MVP
10. React UI
11. Human-in-the-loop
12. Memory and RAG
13. Security hardening
14. Testing
15. Docker
16. CI/CD
17. Final audit

Do not implement the entire project in one generation.

After each phase:

1. Run tests.
2. Check integration.
3. Review architecture.
4. Update documentation.
5. Report known limitations.

---

# Critical Acceptance Principle

The most important product requirement is:

THE UI MUST VISUALIZE THE REAL AGENT RUNTIME.

The following must be real:

- Skill selection
- Hook execution
- Tool execution
- LangGraph state transitions
- Event generation
- Event persistence
- WebSocket streaming
- Workflow visualization

Do not replace real functionality with hard-coded demonstrations.