"""
Fetches stock data from two sources:
  1. NASDAQ screener API  → initial stock universe (ticker, name, sector, industry)
  2. yfinance             → enriched info + real-time metrics
"""
import asyncio
import logging

import aiohttp
import yfinance as yf
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.stock import Stock, StockMetrics

logger = logging.getLogger(__name__)

_NASDAQ_SCREENER = "https://api.nasdaq.com/api/screener/stocks"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; market-firehose/1.0)"}
_METRICS_CONCURRENCY = 10  # yfinance requests in flight at once


# ── Universe loading ─────────────────────────────────────────────────────────

async def fetch_exchange_list(exchange: str = "NYSE") -> list[dict]:
    """Pull the full stock list for an exchange from the NASDAQ screener API."""
    params = {"exchange": exchange, "download": "true", "tableonly": "true"}
    async with aiohttp.ClientSession(headers=_HEADERS) as session:
        async with session.get(_NASDAQ_SCREENER, params=params) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)
    rows = data.get("data", {}).get("rows") or []
    logger.info("NASDAQ screener returned %d rows for %s", len(rows), exchange)
    return rows


async def upsert_universe(session: AsyncSession, rows: list[dict]) -> int:
    """Bulk-upsert stock rows from the NASDAQ screener into the stocks table."""
    records = []
    for row in rows:
        ticker = (row.get("symbol") or "").strip().upper()
        if not ticker:
            continue
        records.append({
            "ticker": ticker,
            "name": (row.get("name") or "").strip(),
            "exchange": (row.get("exchange") or "NYSE").strip(),
            "sector": (row.get("sector") or "").strip() or None,
            "industry": (row.get("industry") or "").strip() or None,
        })

    if not records:
        return 0

    stmt = (
        insert(Stock)
        .values(records)
        .on_conflict_do_update(
            index_elements=["ticker"],
            set_={"name": insert(Stock).excluded.name,
                  "sector": insert(Stock).excluded.sector,
                  "industry": insert(Stock).excluded.industry},
        )
    )
    await session.execute(stmt)
    return len(records)


# ── Per-ticker enrichment (yfinance) ─────────────────────────────────────────

def _parse_info(info: dict) -> tuple[dict, dict]:
    """Split a yfinance info dict into (stock_fields, metrics_fields)."""
    stock = {
        "description": (info.get("longBusinessSummary") or "")[:4000] or None,
        "website": info.get("website"),
        "exchange": info.get("exchange"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "name": info.get("longName") or info.get("shortName"),
    }
    metrics = {
        "market_cap": info.get("marketCap"),
        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "volume": info.get("volume") or info.get("regularMarketVolume"),
        "avg_volume": info.get("averageVolume"),
        "pe_ratio": info.get("trailingPE"),
        "dividend_yield": info.get("dividendYield"),
        "week52_high": info.get("fiftyTwoWeekHigh"),
        "week52_low": info.get("fiftyTwoWeekLow"),
    }
    return stock, metrics


async def fetch_and_store_ticker(ticker: str, session: AsyncSession) -> bool:
    """Fetch full yfinance info for one ticker and upsert into DB."""
    try:
        info = await asyncio.to_thread(lambda: yf.Ticker(ticker).info)
        if not info or info.get("quoteType") not in ("EQUITY", "ETF"):
            return False
        stock_fields, metric_fields = _parse_info(info)

        await session.execute(
            insert(Stock)
            .values(ticker=ticker, name=stock_fields.get("name") or ticker, **{
                k: v for k, v in stock_fields.items() if k != "name"
            })
            .on_conflict_do_update(
                index_elements=["ticker"],
                set_={k: v for k, v in stock_fields.items() if v is not None},
            )
        )
        await session.execute(
            insert(StockMetrics)
            .values(ticker=ticker, **metric_fields)
            .on_conflict_do_update(
                index_elements=["ticker"],
                set_={k: v for k, v in metric_fields.items() if v is not None},
            )
        )
        return True
    except Exception:
        logger.debug("yfinance failed for %s", ticker, exc_info=True)
        return False


async def bulk_update_metrics(tickers: list[str], session: AsyncSession) -> int:
    """Update metrics for a list of tickers with bounded concurrency."""
    sem = asyncio.Semaphore(_METRICS_CONCURRENCY)

    async def _one(ticker: str) -> bool:
        async with sem:
            return await fetch_and_store_ticker(ticker, session)

    results = await asyncio.gather(*[_one(t) for t in tickers])
    ok = sum(results)
    logger.info("Metrics updated: %d/%d tickers", ok, len(tickers))
    return ok
