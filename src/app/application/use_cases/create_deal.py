from datetime import date
from decimal import Decimal

from app.application.dto import CreateDealCommand
from app.application.ports import Clock, UnitOfWork
from app.domain.entities import Deal
from app.domain.exceptions import RatesNotAvailableError, UnsupportedCurrencyError
from app.domain.value_objects import BYN, CurrencyCode, ExchangeRate


class CreateDeal:
    """Quote an exchange at today's NBRB rates and store it as a pending deal"""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def __call__(self, cmd: CreateDealCommand) -> Deal:
        from_code = CurrencyCode(cmd.from_currency)
        to_code = CurrencyCode(cmd.to_currency)
        now = self._clock.now()
        today = now.date()

        async with self._uow:
            from_rate = await self._get_rate(from_code, today)
            to_rate = await self._get_rate(to_code, today)
            deal = Deal.create(cmd.amount, from_rate, to_rate, now)
            await self._uow.deals.add(deal)
            await self._uow.commit()
        return deal

    async def _get_rate(self, code: CurrencyCode, on_date: date) -> ExchangeRate:
        """Rate of the currency to BYN. Must be called inside an open unit of work"""
        if code == BYN:
            return ExchangeRate(on_date, BYN, 1, Decimal(1))

        rate = await self._uow.rates.get(code, on_date)
        if rate is not None:
            return rate
        if not await self._uow.rates.exists(on_date):
            raise RatesNotAvailableError(on_date)
        raise UnsupportedCurrencyError(code.code)
