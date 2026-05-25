"""
Natural-language stock search.

Flow:
  user query
    → LLM returns { tickers, sector, industry_hint, min/max_market_cap, reasoning }
    → missing tickers fetched on-demand from yfinance
    → DB rows returned with full metrics
"""
import json
import logging
from typing import Optional

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.models.stock import Stock, StockMetrics
from src.research.fetcher import fetch_and_store_ticker

logger = logging.getLogger(__name__)

_SYSTEM = """\
You are a financial research assistant specializing in US-listed equities.

Given a natural language query about stocks, return ONLY a valid JSON object — no markdown, no extra text:

{
  "tickers":        ["TICKER", ...],
  "sector":         "<sector name or null>",
  "industry_hint":  "<free-text industry description or null>",
  "min_market_cap": <integer USD or null>,
  "max_market_cap": <integer USD or null>,
  "reasoning":      "<1-2 sentence explanation>"
}

Rules:
- tickers: up to 20 specific US-listed ticker symbols you are highly confident about.
  For broad queries ("all tech stocks") return [] and use sector/industry_hint instead.
- sector: use standard GICS sector names (Technology, Healthcare, Financials, Energy,
  Consumer Discretionary, Consumer Staples, Industrials, Materials, Real Estate,
  Utilities, Communication Services).
- Market cap qualifiers: "mega cap" > $200B, "large cap" > $10B, "mid cap" $2B-$10B,
  "small cap" < $2B. Express as integers (e.g. 10000000000).
- Only return valid JSON.
"""


class NLSearchEngine:
    def __init__(self) -> None:
        if settings.llm_provider == "anthropic":
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            self._call = self._call_anthropic
        else:
            import openai
            self._client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
            self._call = self._call_openai

    async def search(
        self,
        query: str,
        session: AsyncSession,
        limit: int = 20,
    ) -> dict:
        parsed = await self._parse_query(query)
        tickers: list[str] = parsed.get("tickers") or []
        sector: Optional[str] = parsed.get("sector")
        industry_hint: Optional[str] = parsed.get("industry_hint")
        min_cap: Optional[int] = parsed.get("min_market_cap")
        max_cap: Optional[int] = parsed.get("max_market_cap")

        # Fetch any tickers not yet in the DB
        if tickers:
            existing = set(
                row[0] for row in (
                    await session.execute(select(Stock.ticker).where(Stock.ticker.in_(tickers)))
                ).all()
            )
            missing = [t for t in tickers if t not in existing]
            for ticker in missing:
                await fetch_and_store_ticker(ticker, session)

        stocks = await _query_stocks(
            session,
            tickers=tickers or None,
            sector=sector,
            industry_hint=industry_hint,
            min_market_cap=min_cap,
            max_market_cap=max_cap,
            limit=limit,
        )

        return {
            "query": query,
            "reasoning": parsed.get("reasoning", ""),
            "results": stocks,
            "total": len(stocks),
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def _parse_query(self, query: str) -> dict:
        raw = await self._call(query)
        return _safe_parse(raw)

    async def _call_anthropic(self, query: str) -> str:
        resp = await self._client.messages.create(
            model=settings.llm_model,
            max_tokens=512,
            system=_SYSTEM,
            messages=[{"role": "user", "content": query}],
        )
        return resp.content[0].text

    async def _call_openai(self, query: str) -> str:
        resp = await self._client.chat.completions.create(
            model=settings.llm_model,
            max_tokens=512,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": query},
            ],
        )
        return resp.choices[0].message.content or ""


async def _query_stocks(
    session: AsyncSession,
    tickers: Optional[list[str]],
    sector: Optional[str],
    industry_hint: Optional[str],
    min_market_cap: Optional[int],
    max_market_cap: Optional[int],
    limit: int,
) -> list[dict]:
    q = (
        select(Stock, StockMetrics)
        .outerjoin(StockMetrics, Stock.ticker == StockMetrics.ticker)
    )
    if tickers:
        q = q.where(Stock.ticker.in_(tickers))
    if sector:
        q = q.where(Stock.sector.ilike(f"%{sector}%"))
    if industry_hint:
        q = q.where(Stock.industry.ilike(f"%{industry_hint}%"))
    if min_market_cap is not None:
        q = q.where(StockMetrics.market_cap >= min_market_cap)
    if max_market_cap is not None:
        q = q.where(StockMetrics.market_cap <= max_market_cap)

    # Prefer stocks with metrics; sort by market cap desc
    q = q.order_by(StockMetrics.market_cap.desc().nulls_last()).limit(limit)

    rows = (await session.execute(q)).all()
    return [_row_to_dict(stock, metrics) for stock, metrics in rows]


def _row_to_dict(stock: Stock, metrics: Optional[StockMetrics]) -> dict:
    return {
        "ticker": stock.ticker,
        "name": stock.name,
        "exchange": stock.exchange,
        "sector": stock.sector,
        "industry": stock.industry,
        "description": stock.description,
        "website": stock.website,
        "metrics": {
            "market_cap": getattr(metrics, "market_cap", None),
            "price": float(metrics.price) if getattr(metrics, "price", None) else None,
            "volume": getattr(metrics, "volume", None),
            "avg_volume": getattr(metrics, "avg_volume", None),
            "pe_ratio": float(metrics.pe_ratio) if getattr(metrics, "pe_ratio", None) else None,
            "dividend_yield": float(metrics.dividend_yield) if getattr(metrics, "dividend_yield", None) else None,
            "week52_high": float(metrics.week52_high) if getattr(metrics, "week52_high", None) else None,
            "week52_low": float(metrics.week52_low) if getattr(metrics, "week52_low", None) else None,
            "updated_at": metrics.updated_at.isoformat() if getattr(metrics, "updated_at", None) else None,
        } if metrics else None,
    }


def _safe_parse(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    logger.warning("Could not parse LLM response: %s", text[:300])
    return {}
