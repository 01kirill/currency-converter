from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import exists, func, literal, select, union_all, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dto import CurrencyReportRow
from app.domain.entities import Deal
from app.domain.value_objects import CurrencyCode, DealStatus, ExchangeRate
from app.infrastructure.clock import MINSK
from app.infrastructure.db.models import DealORM, RateORM


def _rate_to_domain(row: RateORM) -> ExchangeRate:
    return ExchangeRate(row.rate_date, CurrencyCode(row.currency_code), row.scale, row.rate)


def _deal_to_domain(row: DealORM) -> Deal:
    return Deal(
        id=row.id,
        amount=row.amount,
        rate=row.rate,
        from_currency=CurrencyCode(row.from_currency),
        to_currency=CurrencyCode(row.to_currency),
        converted_amount=row.converted_amount,
        status=DealStatus(row.status),
        created_at=row.created_at,
        resolved_at=row.resolved_at,
    )


class SqlAlchemyRateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_many(self, rates: Sequence[ExchangeRate]) -> None:
        if not rates:
            return
        values = [
            {
                "currency_code": rate.currency_code.code,
                "rate_date": rate.rate_date,
                "scale": rate.scale,
                "rate": rate.rate,
            }
            for rate in rates
        ]
        stmt = insert(RateORM).values(values).on_conflict_do_nothing()
        await self._session.execute(stmt)

    async def exists(self, on_date: date) -> bool:
        stmt = select(exists().where(RateORM.rate_date == on_date))
        return bool(await self._session.scalar(stmt))

    async def get(self, code: CurrencyCode, on_date: date) -> ExchangeRate | None:
        row = await self._session.get(RateORM, (code.code, on_date))
        return _rate_to_domain(row) if row is not None else None


class SqlAlchemyDealRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, deal: Deal) -> None:
        self._session.add(
            DealORM(
                id=deal.id,
                amount=deal.amount,
                from_currency=deal.from_currency.code,
                to_currency=deal.to_currency.code,
                rate=deal.rate,
                converted_amount=deal.converted_amount,
                status=deal.status.value,
                created_at=deal.created_at,
                resolved_at=deal.resolved_at,
            )
        )

    async def get_for_update(self, deal_id: UUID) -> Deal | None:
        stmt = select(DealORM).where(DealORM.id == deal_id).with_for_update()
        row = await self._session.scalar(stmt)
        return _deal_to_domain(row) if row is not None else None

    async def update(self, deal: Deal) -> None:
        stmt = (
            update(DealORM)
            .where(DealORM.id == deal.id)
            .values(status=deal.status.value, resolved_at=deal.resolved_at)
        )
        await self._session.execute(stmt)

    async def list_pending(self) -> list[Deal]:
        stmt = (
            select(DealORM)
            .where(DealORM.status == DealStatus.PENDING.value)
            .order_by(DealORM.created_at)
        )
        rows = await self._session.scalars(stmt)
        return [_deal_to_domain(row) for row in rows]

    async def report(
        self, date_from: date, date_to: date, currency: CurrencyCode | None
    ) -> list[CurrencyReportRow]:
        start = datetime.combine(date_from, time.min, tzinfo=MINSK)
        end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=MINSK)
        accepted_in_period = (
            DealORM.status == DealStatus.ACCEPTED.value,
            DealORM.resolved_at >= start,
            DealORM.resolved_at < end,
        )
        zero = literal(Decimal(0))
        received = select(
            DealORM.from_currency.label("currency"),
            DealORM.amount.label("received"),
            zero.label("paid_out"),
        ).where(*accepted_in_period)
        paid_out = select(DealORM.to_currency, zero, DealORM.converted_amount).where(
            *accepted_in_period
        )
        moves = union_all(received, paid_out).subquery()

        stmt = (
            select(
                moves.c.currency,
                func.sum(moves.c.received),
                func.sum(moves.c.paid_out),
                func.count(),
            )
            .group_by(moves.c.currency)
            .order_by(moves.c.currency)
        )
        if currency is not None:
            stmt = stmt.where(moves.c.currency == currency.code)

        rows = await self._session.execute(stmt)
        return [
            CurrencyReportRow(CurrencyCode(code), received_sum, paid_out_sum, count)
            for code, received_sum, paid_out_sum, count in rows
        ]
