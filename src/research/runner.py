"""Background service: refreshes the NYSE stock universe and metrics on a schedule."""
import asyncio
import logging
import sys

from src.config import settings
from src.research.fetcher import fetch_exchange_list, upsert_universe, bulk_update_metrics
from src.storage.database import get_session
from sqlalchemy import select, text
from src.models.stock import Stock

logging.basicConfig(level=settings.log_level, stream=sys.stdout,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

UNIVERSE_REFRESH_INTERVAL = 24 * 3600   # 24 h
METRICS_REFRESH_INTERVAL  = 3600        # 1 h


async def refresh_universe() -> None:
    logger.info("Refreshing stock universe from NASDAQ screener…")
    rows = await fetch_exchange_list("NYSE")
    async with get_session() as session:
        n = await upsert_universe(session, rows)
    logger.info("Universe upsert complete: %d rows", n)


async def refresh_metrics() -> None:
    logger.info("Refreshing stock metrics via yfinance…")
    async with get_session() as session:
        tickers = [
            row[0] for row in
            (await session.execute(select(Stock.ticker))).all()
        ]
    if not tickers:
        logger.warning("No tickers in DB — run universe refresh first")
        return
    async with get_session() as session:
        n = await bulk_update_metrics(tickers, session)
    logger.info("Metrics refresh complete: %d tickers updated", n)


async def main() -> None:
    # On cold start, seed the universe if the table is empty
    async with get_session() as session:
        count = (await session.execute(text("SELECT COUNT(*) FROM stocks"))).scalar_one()
    if count == 0:
        await refresh_universe()

    async def universe_loop():
        while True:
            await asyncio.sleep(UNIVERSE_REFRESH_INTERVAL)
            await refresh_universe()

    async def metrics_loop():
        await asyncio.sleep(60)   # brief delay so universe is ready
        while True:
            await refresh_metrics()
            await asyncio.sleep(METRICS_REFRESH_INTERVAL)

    await asyncio.gather(universe_loop(), metrics_loop())


if __name__ == "__main__":
    asyncio.run(main())
