import logging

from app.application.dto import ResolveDealCommand
from app.application.ports import Clock, UnitOfWork
from app.domain.entities import Deal
from app.domain.exceptions import DealNotFoundError

logger = logging.getLogger(__name__)


class ResolveDeal:
    """Accept or decline a pending deal"""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def __call__(self, cmd: ResolveDealCommand) -> Deal:
        now = self._clock.now()
        async with self._uow:
            deal = await self._uow.deals.get_for_update(cmd.deal_id)
            if deal is None:
                raise DealNotFoundError(cmd.deal_id)
            if cmd.accept:
                deal.accept(now)
            else:
                deal.decline(now)
            await self._uow.deals.update(deal)
            await self._uow.commit()
        logger.info("Deal %s %s", deal.id, deal.status.value)
        return deal
