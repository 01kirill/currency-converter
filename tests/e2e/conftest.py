from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.dependencies import get_clock
from app.main import create_app
from tests.fakes import FixedClock


@pytest.fixture
async def client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncClient]:
    """HTTP client to the real app on the test database, with the clock fixed at NOW"""
    app = create_app()
    app.state.session_factory = session_factory
    app.dependency_overrides[get_clock] = lambda: FixedClock()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
