# Agent Skills & Hooks Playground

An interactive platform for understanding, demonstrating, and visualizing how modern AI agent systems work internally.

The platform demonstrates the real execution lifecycle of an AI agent, including:

- Agent reasoning and orchestration (LangGraph)
- Skill selection and execution
- Lifecycle hooks (before/after interception)
- Tool calling with permission checks
- Conditional routing and retry loops
- Human-in-the-loop approval
- Memory and RAG
- Real-time execution tracing
- Live workflow visualization (React Flow)

## Quick Start

```bash
cp .env.example .env
cd backend
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

## Documentation

- [Architecture](docs/architecture.md)
- [API Reference](docs/api.md)
- [Development Guide](docs/development.md)

## Architecture

```
User -> FastAPI -> LangGraph Runtime -> Skills / Hooks / Tools -> LLM Providers
                     |
                  Observability (Events)
                     |
              Database + WebSocket -> React UI
```

## Status

Foundation phase complete. FastAPI application with SQLAlchemy, Alembic, health endpoint,
Docker, CI/CD, and testing infrastructure are operational.
