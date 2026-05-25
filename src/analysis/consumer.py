"""
High-throughput Kafka consumer for market analysis.

Throughput design:
  - getmany() pulls up to BATCH_SIZE messages per loop tick
  - asyncio.gather() processes the whole batch concurrently
  - ArticleAnalyzer._sem caps LLM concurrency (default 20)
  - Scale horizontally: run multiple replicas — same consumer group,
    Kafka distributes partitions across them automatically
"""
import asyncio
import json
import logging
import sys

import redis.asyncio as aioredis
from aiokafka import AIOKafkaConsumer

from src.analysis.processor import ArticleAnalyzer
from src.analysis.store import publish_analysis, save_analysis
from src.config import settings
from src.storage.database import get_session

logging.basicConfig(
    level=settings.log_level, stream=sys.stdout,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    analyzer = ArticleAnalyzer()
    redis = aioredis.from_url(settings.redis_url, decode_responses=True)

    consumer = AIOKafkaConsumer(
        settings.kafka_topic_processed,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_analysis_group,
        value_deserializer=lambda v: json.loads(v.decode()),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )
    await consumer.start()
    logger.info(
        "Analysis consumer ready — topic='%s' concurrency=%d batch=%d",
        settings.kafka_topic_processed,
        settings.analysis_concurrency,
        settings.analysis_batch_size,
    )

    try:
        while True:
            batch = await consumer.getmany(
                timeout_ms=500,
                max_records=settings.analysis_batch_size,
            )
            if not batch:
                continue

            messages = [msg for msgs in batch.values() for msg in msgs]
            if not messages:
                continue

            logger.debug("Processing batch of %d articles", len(messages))
            await asyncio.gather(
                *[_handle(msg.value, analyzer, redis) for msg in messages],
                return_exceptions=True,
            )
    finally:
        await consumer.stop()
        await redis.aclose()


async def _handle(payload: dict, analyzer: ArticleAnalyzer, redis) -> None:
    article_id = payload.get("article_id")
    title = payload.get("title", "")
    if not article_id or not title:
        logger.warning("Skipping malformed payload: %s", payload)
        return
    try:
        data = await analyzer.analyze(
            article_id=article_id,
            title=title,
            body=payload.get("body"),
            summary=payload.get("summary"),
        )
        async with get_session() as session:
            analysis_id = await save_analysis(session, data)
        if analysis_id:
            await publish_analysis(redis, data, analysis_id)
            logger.info(
                "Analysed article %s → event=%s companies=%d",
                article_id, data.get("event_type"), len(data.get("companies") or []),
            )
    except Exception:
        logger.exception("Analysis failed for article_id=%s", article_id)


if __name__ == "__main__":
    asyncio.run(main())
