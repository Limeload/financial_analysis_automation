"""Metric-based stock screener — pure DB query, no LLM involved."""
from typing import Optional

from sqlalchemy import select, func, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.stock import Stock, StockMetrics
from src.research.nl_search import _row_to_dict

SORT_FIELDS = {
    "market_cap": StockMetrics.market_cap,
    "volume": StockMetrics.volume,
    "price": StockMetrics.price,
    "pe_ratio": StockMetrics.pe_ratio,
    "dividend_yield": StockMetrics.dividend_yield,
    "ticker": Stock.ticker,
    "name": Stock.name,
}


async def screen(
    session: AsyncSession,
    *,
    sector: Optional[str] = None,
    industry: Optional[str] = None,
    exchange: Optional[str] = None,
    min_market_cap: Optional[int] = None,
    max_market_cap: Optional[int] = None,
    min_volume: Optional[int] = None,
    max_volume: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_pe: Optional[float] = None,
    max_pe: Optional[float] = None,
    min_dividend_yield: Optional[float] = None,
    sort_by: str = "market_cap",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[dict], int]:

    base = (
        select(Stock, StockMetrics)
        .outerjoin(StockMetrics, Stock.ticker == StockMetrics.ticker)
    )
    count_q = (
        select(func.count())
        .select_from(Stock)
        .outerjoin(StockMetrics, Stock.ticker == StockMetrics.ticker)
    )

    filters = []
    if sector:
        filters.append(Stock.sector.ilike(f"%{sector}%"))
    if industry:
        filters.append(Stock.industry.ilike(f"%{industry}%"))
    if exchange:
        filters.append(Stock.exchange.ilike(f"%{exchange}%"))
    if min_market_cap is not None:
        filters.append(StockMetrics.market_cap >= min_market_cap)
    if max_market_cap is not None:
        filters.append(StockMetrics.market_cap <= max_market_cap)
    if min_volume is not None:
        filters.append(StockMetrics.volume >= min_volume)
    if max_volume is not None:
        filters.append(StockMetrics.volume <= max_volume)
    if min_price is not None:
        filters.append(StockMetrics.price >= min_price)
    if max_price is not None:
        filters.append(StockMetrics.price <= max_price)
    if min_pe is not None:
        filters.append(StockMetrics.pe_ratio >= min_pe)
    if max_pe is not None:
        filters.append(StockMetrics.pe_ratio <= max_pe)
    if min_dividend_yield is not None:
        filters.append(StockMetrics.dividend_yield >= min_dividend_yield)

    for f in filters:
        base = base.where(f)
        count_q = count_q.where(f)

    sort_col = SORT_FIELDS.get(sort_by, StockMetrics.market_cap)
    order = desc(sort_col).nulls_last() if sort_dir == "desc" else asc(sort_col).nulls_last()

    total = (await session.execute(count_q)).scalar_one()
    rows = (
        await session.execute(
            base.order_by(order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    return [_row_to_dict(s, m) for s, m in rows], total
