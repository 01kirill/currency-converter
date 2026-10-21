from collections.abc import AsyncIterator

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.infrastructure.config import Settings
from app.infrastructure.db.models import Base
from app.infrastructure.db.uow import SqlAlchemyUnitOfWork


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Empty tables in the test database, cleaned after each test"""
    try:
        settings = Settings()  # pyright: ignore[reportCallIssue]
    except ValidationError:
        pytest.skip("Database settings are missing: cp .env.example .env")
    url = settings.database_url.set(database=f"{settings.postgres_db}_test")
    engine = create_async_engine(url, poolclass=NullPool)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except OSError:
        await engine.dispose()
        pytest.skip("PostgreSQL is not available: run: docker compose up -d db")

    yield async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE rates, deals"))
    await engine.dispose()


@pytest.fixture
def uow(session_factory: async_sessionmaker[AsyncSession]) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(session_factory)
