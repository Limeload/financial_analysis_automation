"""Persist analysis results and publish to Redis."""
import json
import logging

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.analysis import ArticleAnalysis, ArticleCompanySentiment

logger = logging.getLogger(__name__)


async def save_analysis(session: AsyncSession, data: dict) -> int | None:
    """
    Upsert one analysis record + its company sentiments.
    Returns the analysis ID, or None if this article was already analysed.
    """
    article_id: int = data["article_id"]
    event_type: str = data.get("event_type") or "other"
    event_confidence = data.get("event_confidence")
    companies: list[dict] = data.get("companies") or []

    try:
        result = await session.execute(
            insert(ArticleAnalysis)
            .values(
                article_id=article_id,
                event_type=event_type,
                event_confidence=event_confidence,
            )
            .on_conflict_do_nothing(constraint="uq_analysis_article")
            .returning(ArticleAnalysis.id)
        )
        row = result.fetchone()
        if row is None:
            logger.debug("Article %s already analysed — skipping", article_id)
            return None
        analysis_id: int = row[0]
    except IntegrityError:
        return None

    if companies:
        sentiment_rows = [
            {
                "article_id": article_id,
                "analysis_id": analysis_id,
                "company_name": c.get("name", "")[:255],
                "ticker": (c.get("ticker") or "")[:16] or None,
                "sentiment": c.get("sentiment", "neutral"),
                "sentiment_score": _clamp(c.get("sentiment_score")),
                "reason": (c.get("reason") or "")[:2000] or None,
            }
            for c in companies
            if c.get("name")
        ]
        if sentiment_rows:
            await session.execute(
                insert(ArticleCompanySentiment)
                .values(sentiment_rows)
                .on_conflict_do_nothing()
            )

    return analysis_id


async def publish_analysis(redis, data: dict, analysis_id: int) -> None:
    payload = json.dumps({**data, "analysis_id": analysis_id})
    await redis.publish("article-analyses", payload)


def _clamp(v) -> float | None:
    if v is None:
        return None
    try:
        return max(-1.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return None
