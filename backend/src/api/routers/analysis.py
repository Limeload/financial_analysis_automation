import json
import logging
from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import and_, desc, func, select

from src.api.dependencies import require_api_key
from src.config import settings
from src.models.analysis import EVENT_TYPES, ArticleAnalysis, ArticleCompanySentiment
from src.models.article import Article
from src.storage.database import get_session

router = APIRouter(prefix="/analysis", tags=["analysis"])
logger = logging.getLogger(__name__)

_AUTH = {401: {"description": "Missing or invalid X-API-Key"}}
_NOT_FOUND = {404: {"description": "Not found"}}


# ── Article analysis ─────────────────────────────────────────────────────────

@router.get(
    "/articles/{article_id}",
    summary="Get analysis for an article",
    description="Returns the event classification and per-company sentiment extracted by Claude.",
    responses={**_AUTH, **_NOT_FOUND},
)
async def get_article_analysis(
    article_id: int,
    _: str = Depends(require_api_key),
):
    async with get_session() as session:
        analysis = (
            await session.execute(
                select(ArticleAnalysis).where(ArticleAnalysis.article_id == article_id)
            )
        ).scalar_one_or_none()
        if not analysis:
            raise HTTPException(404, "Analysis not found — article may not have been processed yet")

        sentiments = (
            await session.execute(
                select(ArticleCompanySentiment).where(
                    ArticleCompanySentiment.analysis_id == analysis.id
                )
            )
        ).scalars().all()

    return {
        "article_id": article_id,
        "event_type": analysis.event_type,
        "event_confidence": float(analysis.event_confidence) if analysis.event_confidence else None,
        "processed_at": analysis.processed_at.isoformat(),
        "companies": [_fmt_sentiment(s) for s in sentiments],
    }


# ── Company sentiment ─────────────────────────────────────────────────────────

@router.get(
    "/companies/{ticker}/sentiment",
    summary="Company sentiment feed",
    description=(
        "Recent articles mentioning this ticker, with per-article sentiment. "
        "Useful for building a sentiment timeline for a stock."
    ),
    responses={**_AUTH},
)
async def get_company_sentiment(
    ticker: str,
    days: int = Query(7, ge=1, le=90, description="Look-back window in days"),
    sentiment: str | None = Query(None, description="Filter: positive | negative | neutral"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: str = Depends(require_api_key),
):
    from datetime import datetime, timedelta
    since = datetime.now(UTC) - timedelta(days=days)
    ticker = ticker.upper()

    async with get_session() as session:
        q = (
            select(ArticleCompanySentiment, ArticleAnalysis, Article)
            .join(ArticleAnalysis, ArticleCompanySentiment.analysis_id == ArticleAnalysis.id)
            .join(Article, ArticleCompanySentiment.article_id == Article.id)
            .where(
                and_(
                    ArticleCompanySentiment.ticker == ticker,
                    ArticleAnalysis.processed_at >= since,
                )
            )
        )
        if sentiment:
            q = q.where(ArticleCompanySentiment.sentiment == sentiment)

        total = (
            await session.execute(
                select(func.count()).select_from(q.subquery())
            )
        ).scalar_one()

        rows = (
            await session.execute(
                q.order_by(desc(ArticleAnalysis.processed_at))
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()

    return {
        "ticker": ticker,
        "days": days,
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "article_id": s.article_id,
                "title": art.title,
                "published_at": art.published_at.isoformat() if art.published_at else None,
                "sentiment": s.sentiment,
                "sentiment_score": float(s.sentiment_score) if s.sentiment_score else 0.0,
                "reason": s.reason,
                "event_type": a.event_type,
            }
            for s, a, art in rows
        ],
    }


@router.get(
    "/companies/{ticker}/summary",
    summary="Aggregated sentiment summary",
    description=(
        "Counts and average score across positive/negative/neutral mentions "
        "for the given look-back window. Quick signal for sentiment trend."
    ),
    responses=_AUTH,
)
async def get_company_summary(
    ticker: str,
    days: int = Query(7, ge=1, le=90),
    _: str = Depends(require_api_key),
):
    from datetime import datetime, timedelta
    since = datetime.now(UTC) - timedelta(days=days)
    ticker = ticker.upper()

    async with get_session() as session:
        rows = (
            await session.execute(
                select(
                    ArticleCompanySentiment.sentiment,
                    func.count().label("count"),
                    func.avg(ArticleCompanySentiment.sentiment_score).label("avg_score"),
                )
                .join(ArticleAnalysis, ArticleCompanySentiment.analysis_id == ArticleAnalysis.id)
                .where(
                    and_(
                        ArticleCompanySentiment.ticker == ticker,
                        ArticleAnalysis.processed_at >= since,
                    )
                )
                .group_by(ArticleCompanySentiment.sentiment)
            )
        ).all()

    counts = {r.sentiment: {"count": r.count, "avg_score": round(float(r.avg_score), 3)} for r in rows}
    total = sum(v["count"] for v in counts.values())
    weighted_score = round(
        sum(v["avg_score"] * v["count"] for v in counts.values()) / total, 3
    ) if total else 0.0
    return {
        "ticker": ticker,
        "days": days,
        "total": total,
        "positive": counts.get("positive", {}).get("count", 0),
        "negative": counts.get("negative", {}).get("count", 0),
        "neutral": counts.get("neutral", {}).get("count", 0),
        "weighted_score": weighted_score,
    }


# ── Events feed ───────────────────────────────────────────────────────────────

@router.get(
    "/events",
    summary="Browse events by type",
    description=(
        f"Filter recent events by type. Valid types: `{'`, `'.join(EVENT_TYPES)}`."
    ),
    responses=_AUTH,
)
async def list_events(
    event_type: str | None = Query(None, description="Event type filter"),
    days: int = Query(1, ge=1, le=30),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: str = Depends(require_api_key),
):
    from datetime import datetime, timedelta
    since = datetime.now(UTC) - timedelta(days=days)

    async with get_session() as session:
        q = (
            select(ArticleAnalysis, Article)
            .join(Article, ArticleAnalysis.article_id == Article.id)
            .where(ArticleAnalysis.processed_at >= since)
        )
        if event_type:
            q = q.where(ArticleAnalysis.event_type == event_type)

        total = (await session.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
        rows = (
            await session.execute(
                q.order_by(desc(ArticleAnalysis.processed_at))
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()

        analyses = [r[0] for r in rows]
        articles_by_id = {r[1].id: r[1] for r in rows}

        ids = [a.id for a in analyses]
        sents = (
            await session.execute(
                select(ArticleCompanySentiment).where(
                    ArticleCompanySentiment.analysis_id.in_(ids)
                )
            )
        ).scalars().all()

    tickers_by_analysis: dict[int, list[str]] = {}
    for s in sents:
        tickers_by_analysis.setdefault(s.analysis_id, []).append(
            s.ticker or s.company_name or ""
        )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "article_id": a.article_id,
                "title": articles_by_id[a.article_id].title,
                "published_at": articles_by_id[a.article_id].published_at.isoformat()
                    if articles_by_id[a.article_id].published_at else None,
                "source": articles_by_id[a.article_id].source,
                "event_type": a.event_type,
                "event_confidence": float(a.event_confidence) if a.event_confidence else None,
                "companies": tickers_by_analysis.get(a.id, []),
            }
            for a in analyses
        ],
    }


# ── Real-time WebSocket stream ─────────────────────────────────────────────────

@router.websocket("/stream")
async def analysis_stream(
    websocket: WebSocket,
    api_key: str = Query(..., description="Your API key"),
    ticker: str | None = Query(None, description="Filter by company ticker"),
    event_type: str | None = Query(None, description="Filter by event type"),
):
    """
    **WebSocket** — live stream of article analyses as they are produced.

    Each message is a JSON object containing `article_id`, `event_type`,
    `event_confidence`, and `companies` (with sentiment per company).

    **Connect:**
    ```
    ws://localhost:8000/analysis/stream?api_key=your-key
    ws://localhost:8000/analysis/stream?api_key=your-key&ticker=AAPL
    ws://localhost:8000/analysis/stream?api_key=your-key&event_type=earnings_release
    ```
    """
    if api_key not in settings.api_key_set:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    import redis.asyncio as aioredis
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("article-analyses")
    logger.info("Analysis WS connected (ticker=%s event_type=%s)", ticker, event_type)

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            data = json.loads(message["data"])

            # Apply optional filters
            if event_type and data.get("event_type") != event_type:
                continue
            if ticker:
                tickers_in_msg = {
                    (c.get("ticker") or "").upper()
                    for c in (data.get("companies") or [])
                }
                if ticker.upper() not in tickers_in_msg:
                    continue

            await websocket.send_text(json.dumps(data))
    except WebSocketDisconnect:
        logger.info("Analysis WS disconnected")
    finally:
        await pubsub.unsubscribe("article-analyses")
        await pubsub.aclose()
        await r.aclose()


def _fmt_sentiment(s: ArticleCompanySentiment) -> dict:
    return {
        "company_name": s.company_name,
        "ticker": s.ticker,
        "sentiment": s.sentiment,
        "sentiment_score": float(s.sentiment_score) if s.sentiment_score else None,
        "reason": s.reason,
    }
