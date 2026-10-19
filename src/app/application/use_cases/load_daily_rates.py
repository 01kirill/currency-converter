from app.application.ports import Clock, RatesProvider, UnitOfWork


class LoadDailyRates:
    """Load today's official NBRB rates into storage, once per day(idempotent)"""

    def __init__(self, uow: UnitOfWork, provider: RatesProvider, clock: Clock) -> None:
        self._uow = uow
        self._provider = provider
        self._clock = clock

    async def __call__(self) -> int:
        """Return the number of loaded rates, 0 if today's rates were already stored"""
        today = self._clock.now().date()

        async with self._uow:
            if await self._uow.rates.exists(today):
                return 0

        rates = await self._provider.fetch(today)
        async with self._uow:
            await self._uow.rates.add_many(rates)
            await self._uow.commit()
        return len(rates)
