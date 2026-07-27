# Security Documentation

## Security Model

This application implements a **defense-in-depth** approach to security. No single layer is relied upon exclusively.

## Mitigations Implemented

### 1. Authentication (`backend/app/security/auth.py`)

- API key authentication via `X-API-Key` header on all endpoints
- HMAC-comparison (timing-safe) to prevent timing attacks
- Development mode bypass: when `api_key=dev-key-change-me` and `environment=development`, auth is skipped
- WebSocket connections require API key via header or `api_key` query parameter, plus origin validation

### 2. Python Execution Sandbox (`backend/app/tools/tools/python_execution.py`)

**The sandbox is NOT fully secure and is documented as such.**

Mitigations:
- Static AST analysis blocks: `__import__`, `exec`, `eval`, `compile`, `open`, `input`, `getattr`
- Static AST analysis blocks dunder access: `__class__`, `__base__`, `__subclasses__`, `__globals__`, `__code__`, `__closure__`, `__dict__`
- `getattr` removed from `RESTRICTED_GLOBALS` to prevent string-based dunder access
- Maximum code length: 50,000 characters
- Maximum output length: 100,000 characters
- Tool timeout: 15 seconds
- Permission: `REQUIRE_APPROVAL` — Python execution requires human approval

### 3. File Reader Path Traversal (`backend/app/tools/tools/file_reader.py`)

- `FileReaderTool` is initialized with an `allowed_directory` set to the project root (`BASE_DIR`)
- Relative paths are resolved relative to the allowed directory (not CWD)
- Absolute paths are resolved and checked against `allowed_directory` via `Path.relative_to()`
- Symlinks are resolved before the directory check
- Maximum file size: 1 MB
- No files can be read outside the allowed directory

### 4. Secret Redaction (`backend/app/core/redaction.py`)

Redaction is applied to:
- All events stored in the database
- All events published via WebSocket
- Event metadata

Redaction patterns:
- Generic key=value: `api_key`, `secret`, `token`, `password`, `credential`
- Bearer tokens: `Bearer <token>`
- OpenAI keys: `sk-...`
- Google API keys: `AIza...`
- Credit card numbers (15-16 digits)
- HTTP headers: `x-api-key`, `x-auth-token`, `authorization`

### 5. Request Size Limits (`backend/app/main.py` and Pydantic schemas)

- Maximum request body: 5 MB (enforced by middleware)
- Agent task: max 10,000 characters
- Document title: max 500 characters
- Document content: max 500,000 characters
- Search query: max 10,000 characters
- Skill name / source: max 100-200 characters

### 6. Rate Limiting (`backend/app/security/rate_limit.py`)

- Default: 60 requests per minute per IP
- Rate limiting is disabled in test environment
- Uses `X-Forwarded-For` header when behind a proxy

### 7. CORS (`backend/app/main.py`)

- Allowed origins: configured via `cors_origins` setting (default: `http://localhost:5173,http://localhost:8501`)
- `allow_credentials=True` for WebSocket auth cookies
- Methods and headers are wide open (`*`) — acceptable for API gateway pattern

### 8. Prompt Injection Detection (`backend/app/hooks/hooks/security.py`)

The `SecurityHook` (runs at `before_request` lifecycle event) detects:
- XSS: `<script>` tags
- Path traversal: `../` sequences
- Prompt injection patterns:
  - `ignore/disregard/forget/override all previous instructions`
  - `system prompt/message/instruction` override attempts
  - Role-play patterns: `you are now`, `from now on`, `act as`
  - Jailbreak keywords: `DAN`, `jailbreak`, `bypass`, `breach`, `crack`

### 9. WebSocket Authorization (`backend/app/api/runs.py`)

- API key required via header or query parameter
- Origin validation against `cors_origin_list`
- Connection rejected with code 4001 if auth fails

### 10. Tool Permission Architecture

- `ToolPermissionHook` blocks tools with `DENY` permission
- `HumanApprovalHook` requires approval for `REQUIRE_APPROVAL` tools
- `permission_check` node in LangGraph graph enforces blocks
- `approval_check` node pauses execution for approval-required tools

## Known Limitations (Not Fully Mitigated)

1. **Python execution is NOT sandboxed.** The sandbox uses AST analysis and restricted globals. AST analysis can be bypassed via dynamic execution through Unicode obfuscation, `type()` manipulation, or CPython internals. Full sandboxing would require:
   - `subprocess` execution with OS-level sandboxing (Docker, gVisor, Firecracker)
   - seccomp-bpf syscall filtering
   - Memory and CPU quotas
   - Network disconnection
   - **These are not implemented.**

2. **API key is shared.** There is no per-user or per-tenant authentication. The API key is a single shared secret. If compromised, all API access is compromised.

3. **Prompt injection is detected, not prevented.** The `SecurityHook` uses pattern matching which is inherently limited. Determined prompt injection attempts using encoding, obfuscation, or novel techniques may bypass detection.

4. **HTTPS is not enforced.** All traffic is plain HTTP. In production, a reverse proxy (nginx, Caddy) should terminate TLS.

5. **No Content Security Policy (CSP) headers.** The API does not set CSP headers on responses.

6. **Logging may contain sensitive data.** While the `SecretRedactor` is applied to stored/published events, application logs (`logger.info`, etc.) may contain unredacted data.

7. **Rate limiting is in-memory.** The rate limiter uses an in-memory store. Restarting the server resets all rate limits. For production, use a Redis-backed store.

8. **No input content-type validation.** The system accepts and processes arbitrary string content without validating encoding, character set, or content type beyond what Pydantic provides.

9. **Document/Prompt injection via RAG.** Ingested documents flow into LLM output via RAG retrieval without sanitization. An attacker who can write to the vector store can perform indirect prompt injection.

10. **No network isolation for tools.** The `WebSearchTool` makes outbound HTTP requests with no network restrictions. In a hardened deployment, tool execution should be network-isolated.

## Production Hardening Checklist

Before deploying to production:

- [ ] Set a strong `api_key` in `.env` (not `dev-key-change-me`)
- [ ] Set `environment=production`
- [ ] Configure a reverse proxy (nginx, Caddy) with TLS termination
- [ ] Change `cors_origins` to specific production origins
- [ ] Add Redis-backed rate limiting
- [ ] Run Python execution in a sandboxed subprocess (Docker container)
- [ ] Remove the `dev-key-change-me` bypass from `auth.py`
- [ ] Review and tighten `allow_methods` and `allow_headers` in CORS
- [ ] Add CSP and other security headers to API responses
- [ ] Set up structured logging with a log aggregator
- [ ] Consider adding IP-based allowlisting for sensitive endpoints
