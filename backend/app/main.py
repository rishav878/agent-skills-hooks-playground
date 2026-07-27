import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.hooks.base import LifecycleEvent
from app.hooks.hooks.human_approval import HumanApprovalHook
from app.hooks.hooks.logging_hook import LoggingHook
from app.hooks.hooks.output_validation import OutputValidationHook
from app.hooks.hooks.request_validation import RequestValidationHook
from app.hooks.hooks.security import SecurityHook
from app.hooks.hooks.tool_permission import ToolPermissionHook
from app.hooks.manager import HookManager
from app.security.rate_limit import get_limiter
from app.skills.loader import SkillLoader
from app.tools.loader import ToolLoader


def _register_all_hooks(manager: HookManager) -> None:
    manager.registry.register(RequestValidationHook())
    manager.registry.register(SecurityHook())
    manager.registry.register(ToolPermissionHook())
    manager.registry.register(HumanApprovalHook())
    manager.registry.register(OutputValidationHook())
    for event in LifecycleEvent:
        manager.registry.register(LoggingHook(event))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.info(
        "Starting Agent Skills & Hooks Playground v0.1.0",
        extra={"environment": settings.environment},
    )

    loader = SkillLoader()
    loaded = loader.load_builtins()
    logger.info("Loaded %d builtin skills", len(loaded))
    for s in loaded:
        logger.info("  - %s v%s", s.metadata.name, s.metadata.version)
    app.state.skill_loader = loader

    manager = HookManager()
    _register_all_hooks(manager)
    logger.info("Registered %d hooks", manager.registry.count)
    app.state.hook_manager = manager

    from app.core.config import BASE_DIR

    tool_loader = ToolLoader()
    tool_loader.load_builtins(allowed_directory=str(BASE_DIR))
    logger.info("Loaded %d builtin tools", tool_loader.registry.count)
    for t in tool_loader.registry.list_all():
        logger.info("  - %s (%s, %s)", t.metadata.name, t.metadata.risk_level.value, t.metadata.permission.value)
    app.state.tool_loader = tool_loader

    # Initialize RAG engine
    try:
        from app.embeddings.providers import MockEmbeddingProvider, SentenceTransformerEmbedding

        if settings.embedding_provider == "sentence-transformers":
            embedding = SentenceTransformerEmbedding(model_name=settings.embedding_model)
            logger.info("Using sentence-transformers embedding: %s", settings.embedding_model)
        else:
            embedding = MockEmbeddingProvider()
            logger.info("Using mock embedding provider")

        from app.rag.engine import RAGEngine
        from app.rag.vectorstore import ChromaVectorStore

        vector_store = ChromaVectorStore(embedding)
        rag_engine = RAGEngine(embedding, vector_store)
        app.state.rag_engine = rag_engine
        logger.info("RAG engine initialized")
    except Exception as exc:
        logger.warning("RAG engine initialization failed: %s", exc)
        app.state.rag_engine = None

    yield
    logger.info("Shutting down")


_MAX_REQUEST_BODY = 5 * 1024 * 1024  # 5 MB


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH"):
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > _MAX_REQUEST_BODY:
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Request body too large (max {_MAX_REQUEST_BODY} bytes)"},
                )
        return await call_next(request)


def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please slow down."},
    )


app = FastAPI(
    title="Agent Skills & Hooks Playground",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestSizeLimitMiddleware)

limiter = get_limiter()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

app.include_router(api_router)
