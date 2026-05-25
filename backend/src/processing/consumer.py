"""Kafka consumer: reads raw-articles, enriches with LLM, writes to DB + Redis."""
import asyncio
import json
import logging
import sys

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from src.config import settings
from src.models.schemas import RawArticle
from src.processing.llm_parser import LLMParser
from src.storage.database import get_session, save_article
from src.storage.redis_client import RedisPublisher

logging.basicConfig(level=settings.log_level, stream=sys.stdout,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    parser = LLMParser()
    publisher = RedisPublisher()
    await publisher.connect()

    # Forward processed articles downstream for analysis
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode(),
    )
    await producer.start()

    consumer = AIOKafkaConsumer(
        settings.kafka_topic_raw,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_consumer_group,
        value_deserializer=lambda v: json.loads(v.decode()),
        auto_offset_reset="earliest",
    )
    await consumer.start()
    logger.info("Consumer listening on topic '%s'", settings.kafka_topic_raw)

    try:
        async for msg in consumer:
            await _handle(msg.value, parser, publisher, producer)
    finally:
        await consumer.stop()
        await producer.stop()
        await publisher.close()


async def _handle(
    payload: dict,
    parser: LLMParser,
    publisher: RedisPublisher,
    producer: AIOKafkaProducer,
) -> None:
    try:
        raw = RawArticle.model_validate(payload)
        parsed = await parser.parse(raw)
        async with get_session() as session:
            article_id = await save_article(session, parsed)
        if article_id:
            await publisher.publish(parsed, article_id)
            # Forward compact payload to analysis pipeline
            await producer.send_and_wait(
                settings.kafka_topic_processed,
                {
                    "article_id": article_id,
                    "title": parsed.title,
                    "body": parsed.body,
                    "summary": parsed.summary,
                    "source": parsed.source,
                    "published_at": parsed.published_at.isoformat() if parsed.published_at else None,
                },
            )
            logger.info("Processed article id=%s: %s", article_id, parsed.title[:80])
    except Exception:
        logger.exception("Failed to process message: %s", payload.get("url"))


if __name__ == "__main__":
    asyncio.run(main())
