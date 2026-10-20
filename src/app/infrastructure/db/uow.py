from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db.repositories import SqlAlchemyDealRepository, SqlAlchemyRateRepository


class SqlAlchemyUnitOfWork:
    """One session and one transaction per async with block"""

    deals: SqlAlchemyDealRepository
    rates: SqlAlchemyRateRepository

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.deals = SqlAlchemyDealRepository(self._session)
        self.rates = SqlAlchemyRateRepository(self._session)
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._session.close()

    async def commit(self) -> None:
        await self._session.commit()
