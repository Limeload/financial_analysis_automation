
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select

from src.api.dependencies import require_api_key
from src.models.stock import Stock, StockMetrics
from src.research.nl_search import NLSearchEngine, _row_to_dict
from src.research.screener import SORT_FIELDS, screen
from src.storage.database import get_session

router = APIRouter(prefix="/stocks", tags=["stocks"])

_AUTH = {401: {"description": "Missing or invalid X-API-Key"}}
_NOT_FOUND = {404: {"description": "Ticker not found"}}

_engine: NLSearchEngine | None = None


def _get_engine() -> NLSearchEngine:
    global _engine
    if _engine is None:
        _engine = NLSearchEngine()
    return _engine


@router.get(
    "/search",
    summary="Natural-language stock search",
    description=(
        "Ask in plain English — e.g. *'companies that build data centers'*, "
        "*'large cap pharma stocks'*, *'dividend-paying energy companies'*. "
        "Claude identifies matching tickers, fetches any missing data on-demand from "
        "Yahoo Finance, and returns enriched results with full metrics.\n\n"
        "Tip: be as specific or as broad as you like. The LLM will narrow to tickers "
        "when it can, or fall back to sector/industry filters for broad queries."
    ),
    responses=_AUTH,
)
async def nl_search(
    q: str = Query(..., description="Natural language query", examples=["companies that build data centers"]),
    limit: int = Query(20, ge=1, le=50, description="Max results to return"),
    _: str = Depends(require_api_key),
):
    engine = _get_engine()
    async with get_session() as session:
        result = await engine.search(q, session, limit=limit)
    return result


@router.get(
    "",
    summary="Screen stocks by metrics",
    description=(
        "Filter all NYSE stocks by any combination of: sector, industry, exchange, "
        "market cap, volume, price, P/E ratio, and dividend yield. "
        "Results are sorted by `market_cap` descending by default.\n\n"
        f"Valid `sort_by` values: `{'`, `'.join(SORT_FIELDS)}`."
    ),
    responses=_AUTH,
)
async def screen_stocks(
    sector: str | None = Query(None, description="e.g. Technology, Healthcare, Financials"),
    industry: str | None = Query(None, description="Partial match, e.g. 'semiconductor'"),
    exchange: str | None = Query(None, description="NYSE, NMS (NASDAQ), etc."),
    min_market_cap: int | None = Query(None, description="Minimum market cap in USD"),
    max_market_cap: int | None = Query(None, description="Maximum market cap in USD"),
    min_volume: int | None = Query(None, description="Minimum daily volume"),
    max_volume: int | None = Query(None, description="Maximum daily volume"),
    min_price: float | None = Query(None, description="Minimum share price"),
    max_price: float | None = Query(None, description="Maximum share price"),
    min_pe: float | None = Query(None, description="Minimum trailing P/E ratio"),
    max_pe: float | None = Query(None, description="Maximum trailing P/E ratio"),
    min_dividend_yield: float | None = Query(None, description="Minimum dividend yield (0.02 = 2%)"),
    sort_by: str = Query("market_cap", description="Field to sort by"),
    sort_dir: str = Query("desc", description="asc or desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _: str = Depends(require_api_key),
):
    async with get_session() as session:
        results, total = await screen(
            session,
            sector=sector,
            industry=industry,
            exchange=exchange,
            min_market_cap=min_market_cap,
            max_market_cap=max_market_cap,
            min_volume=min_volume,
            max_volume=max_volume,
            min_price=min_price,
            max_price=max_price,
            min_pe=min_pe,
            max_pe=max_pe,
            min_dividend_yield=min_dividend_yield,
            sort_by=sort_by,
            sort_dir=sort_dir,
            page=page,
            page_size=page_size,
        )
    return {"items": results, "total": total, "page": page, "page_size": page_size}


@router.get(
    "/{ticker}",
    summary="Get stock by ticker",
    description=(
        "Fetch a single stock with its latest metrics. "
        "If the ticker exists on Yahoo Finance but is not yet in the local DB, "
        "it will be fetched and cached on-demand."
    ),
    responses={**_AUTH, **_NOT_FOUND},
)
async def get_stock(
    ticker: str,
    _: str = Depends(require_api_key),
):
    ticker = ticker.upper()
    async with get_session() as session:
        stock = (
            await session.execute(select(Stock).where(Stock.ticker == ticker))
        ).scalar_one_or_none()

        if stock is None:
            from src.research.fetcher import fetch_and_store_ticker
            ok = await fetch_and_store_ticker(ticker, session)
            if not ok:
                raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found")
            stock = (
                await session.execute(select(Stock).where(Stock.ticker == ticker))
            ).scalar_one_or_none()

        metrics = (
            await session.execute(select(StockMetrics).where(StockMetrics.ticker == ticker))
        ).scalar_one_or_none()

    return _row_to_dict(stock, metrics)


@router.post(
    "/refresh",
    summary="Trigger universe refresh",
    description=(
        "Kicks off a background job that pulls the full NYSE stock list from the "
        "NASDAQ screener API and upserts it into the database. "
        "Metrics are updated separately by the scheduled runner. "
        "Returns immediately — the job runs asynchronously."
    ),
    responses=_AUTH,
)
async def trigger_refresh(
    background_tasks: BackgroundTasks,
    _: str = Depends(require_api_key),
):
    from src.research.runner import refresh_universe
    background_tasks.add_task(refresh_universe)
    return {"status": "refresh started"}
