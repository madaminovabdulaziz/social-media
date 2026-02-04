import os
import uuid
from typing import AsyncGenerator

# Set required env vars before any application imports trigger Settings().
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-at-least-32-chars-long!!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import event  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from src.api.deps import get_db_session  # noqa: E402
from src.core import database as _db_mod  # noqa: E402
from src.core.security import create_access_token, hash_password  # noqa: E402
from src.main import app  # noqa: E402
from src.models.base import Base  # noqa: E402
from src.models.user import User  # noqa: E402


@pytest.fixture(scope="module")
async def engine():
    _engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(_engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Inject the test engine into the database module so get_engine() /
    # get_session_factory() work during tests without a real Postgres.
    _db_mod._engine = _engine
    _db_mod._session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    yield _engine

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await _engine.dispose()
    _db_mod._engine = None
    _db_mod._session_factory = None


@pytest.fixture(scope="module")
async def session_factory(engine):
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture()
async def db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            for table in reversed(Base.metadata.sorted_tables):
                await session.execute(table.delete())
            await session.commit()


@pytest.fixture()
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = _override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture()
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="testuser@example.com",
        username="testuser",
        password_hash=hash_password("StrongPass123"),
        full_name="Test User",
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture()
async def second_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="other@example.com",
        username="otheruser",
        password_hash=hash_password("OtherPass123"),
        full_name="Other User",
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture()
async def unverified_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="unverified@example.com",
        username="unverified",
        password_hash=hash_password("UnverifiedPass123"),
        full_name="Unverified User",
        is_verified=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture()
def auth_headers(test_user: User) -> dict[str, str]:
    token = create_access_token(user_id=test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def second_auth_headers(second_user: User) -> dict[str, str]:
    token = create_access_token(user_id=second_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def unverified_auth_headers(unverified_user: User) -> dict[str, str]:
    token = create_access_token(user_id=unverified_user.id)
    return {"Authorization": f"Bearer {token}"}
