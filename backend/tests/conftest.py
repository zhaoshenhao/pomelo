import shutil
import tempfile
from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_session
from app.models import Base
from app.main import app
from app.services import redis_store

# Mutable module globals, set per-test by setup_database.
test_engine = None
test_async_session = None


@pytest_asyncio.fixture(autouse=True)
async def setup_database(tmp_path):
    settings.REDIS_HOST = "127.0.0.1"
    settings.REDIS_PORT = 19999
    settings.REDIS_PASSWORD = ""
    settings.TTS_DEFAULT_VOICE = ""
    redis_store._redis_available = None
    redis_store._redis_client = None

    db_path = tmp_path / "pomelo_test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}", echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    from app import database as _db
    _orig_session = _db.async_session
    _db.async_session = session_factory

    global test_engine, test_async_session
    test_engine = engine
    test_async_session = session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    _db.async_session = _orig_session


@pytest_asyncio.fixture(autouse=True)
async def isolated_docs_root():
    tmp = tempfile.mkdtemp(prefix="pomelo_docs_test_")
    original = settings.DOCS_ROOT
    settings.DOCS_ROOT = tmp
    yield
    settings.DOCS_ROOT = original
    shutil.rmtree(tmp, ignore_errors=True)


async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_async_session() as session:
        yield session


app.dependency_overrides[get_session] = override_get_session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_async_session() as session:
        yield session
