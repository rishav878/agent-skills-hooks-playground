from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.models import Base
from app.database.session import get_session
from app.hooks.base import LifecycleEvent
from app.hooks.hooks.human_approval import HumanApprovalHook
from app.hooks.hooks.logging_hook import LoggingHook
from app.hooks.hooks.output_validation import OutputValidationHook
from app.hooks.hooks.request_validation import RequestValidationHook
from app.hooks.hooks.security import SecurityHook
from app.hooks.hooks.tool_permission import ToolPermissionHook
from app.hooks.manager import HookManager
from app.main import app
from app.skills.loader import SkillLoader
from app.tools.loader import ToolLoader

TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


def _init_app_state() -> None:
    """Initialize the FastAPI app state with skills, hooks, and tools,
    replicating what the lifespan handler does but without needing to
    invoke the ASGI lifespan protocol."""
    loader = SkillLoader()
    loader.load_builtins()
    app.state.skill_loader = loader

    manager = HookManager()
    manager.registry.register(RequestValidationHook())
    manager.registry.register(SecurityHook())
    manager.registry.register(ToolPermissionHook())
    manager.registry.register(HumanApprovalHook())
    manager.registry.register(OutputValidationHook())
    for event in LifecycleEvent:
        manager.registry.register(LoggingHook(event))
    app.state.hook_manager = manager

    tool_loader = ToolLoader()
    tool_loader.load_builtins()
    app.state.tool_loader = tool_loader


def _clear_app_state() -> None:
    app.state.skill_loader = None
    app.state.hook_manager = None
    app.state.tool_loader = None


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    _init_app_state()

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

    _clear_app_state()
