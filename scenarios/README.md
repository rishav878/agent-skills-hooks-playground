# Demo Scenarios

These scripts demonstrate the platform's capabilities.

## 1. Basic Research

Run a research task with the Research skill.

```bash
curl -X POST http://localhost:8000/api/v1/agents/run \
  -H "Content-Type: application/json" \
  -d '{"task": "What are the latest trends in AI?", "parameters": {}}'
```

## 2. Python Execution with Approval

Run a Python execution task that requires human approval.

```bash
curl -X POST http://localhost:8000/api/v1/agents/run \
  -H "Content-Type: application/json" \
  -d '{"task": "Calculate 2 + 2 using Python", "parameters": {}}'
```

Then approve via:

```bash
curl -X POST http://localhost:8000/api/v1/runs/{run_id}/approve \
  -H "X-API-Key: dev-key-change-me"
```

## 3. RAG-Enhanced Research

Ingest a document and run a research task with RAG enabled.

```bash
curl -X POST http://localhost:8000/api/v1/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{"title": "AI Trends", "content": "Key trends in AI include LLMs, RAG, and agentic workflows.", "skill_name": "research"}'

curl -X POST http://localhost:8000/api/v1/agents/run \
  -H "Content-Type: application/json" \
  -d '{"task": "Research AI trends", "parameters": {}}'
```

## 4. Code Review with RAG

Run a code review task with document context.

```bash
curl -X POST http://localhost:8000/api/v1/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{"title": "Python Style Guide", "content": "Use type hints, follow PEP 8, write docstrings.", "skill_name": "code_review"}'

curl -X POST http://localhost:8000/api/v1/agents/run \
  -H "Content-Type: application/json" \
  -d '{"task": "Review a Python file for style issues", "parameters": {}}'
```
