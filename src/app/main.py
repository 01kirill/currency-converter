import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

import httpx
from fastapi import FastAPI

from app.application.use_cases.load_daily_rates import LoadDailyRates
from app.infrastructure.clock import MinskClock
from app.infrastructure.config import Settings
from app.infrastructure.db.session import create_session_factory
from app.infrastructure.db.uow import SqlAlchemyUnitOfWork
from app.infrastructure.nbrb_client import NbrbRatesProvider
from app.infrastructure.scheduler import run_daily_rates
from app.presentation.api import deals, reports
from app.presentation.api.errors import register_error_handlers

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create shared resources on startup, start the rates scheduler, release all on shutdown"""
    settings = Settings()  # pyright: ignore[reportCallIssue]
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    engine, session_factory = create_session_factory(settings.database_url)
    app.state.session_factory = session_factory
    nbrb_client = httpx.AsyncClient(
        base_url=settings.nbrb_base_url,
        timeout=settings.nbrb_timeout_seconds,
    )
    clock = MinskClock()
    load_rates = LoadDailyRates(
        SqlAlchemyUnitOfWork(session_factory),
        NbrbRatesProvider(nbrb_client),
        clock,
    )
    scheduler = asyncio.create_task(
        run_daily_rates(load_rates, clock, settings.rates_retry_seconds),
    )
    logger.info("Service started")
    try:
        yield
    finally:
        scheduler.cancel()
        with suppress(asyncio.CancelledError):
            await scheduler
        await nbrb_client.aclose()
        await engine.dispose()
        logger.info("Service stopped")


def create_app() -> FastAPI:
    app = FastAPI(title="Currency Converter", version="0.1.0", lifespan=lifespan)
    app.include_router(deals.router, prefix="/api/v1")
    app.include_router(reports.router, prefix="/api/v1")
    register_error_handlers(app)
    return app


app = create_app()
