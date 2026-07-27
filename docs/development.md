# Development Guide

## Prerequisites

- Python 3.12+
- Poetry or pip

## Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -e ".[dev]"
```

## Configuration

Copy `.env.example` to `.env` and adjust:

```bash
cp .env.example .env
```

Key settings:
- `DATABASE_URL` — SQLite default (`sqlite+aiosqlite:///./agent_playground.db`)
- `LLM_PROVIDER` — `ollama`, `google`, or `openai`

## Running

```bash
cd backend
uvicorn app.main:app --reload
```

## Database Migrations

```bash
cd backend
alembic upgrade head
alembic revision --autogenerate -m "description"
```

## Testing

```bash
cd backend
pytest ../tests/
pytest --cov=app ../tests/
```

## Linting

```bash
cd backend
ruff check app/ tests/
mypy app/ tests/
```

## Docker

```bash
docker-compose up --build
```
