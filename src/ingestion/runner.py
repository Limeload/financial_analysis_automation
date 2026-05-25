"""Entry point for the ingestion service.

Add more adapters to ADAPTERS to ingest additional feeds.
"""
import asyncio
import logging
import sys

from src.config import settings
from src.ingestion.kafka_producer import ArticleProducer
from src.ingestion.thenewsapi import TheNewsAPIAdapter
from src.ingestion.rss import RSSAdapter

logging.basicConfig(level=settings.log_level, stream=sys.stdout,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RSS_FEEDS = [
    ("https://feeds.bloomberg.com/markets/news.rss", "bloomberg"),
    ("https://feeds.reuters.com/reuters/businessNews", "reuters"),
]


async def main() -> None:
    producer = ArticleProducer()
    await producer.start()

    adapters = [
        TheNewsAPIAdapter(api_key=settings.thenewsapi_key),
        *[RSSAdapter(url, name) for url, name in RSS_FEEDS],
    ]

    tasks = [
        asyncio.create_task(
            adapter.run_forever(producer, settings.ingestion_interval_seconds)
        )
        for adapter in adapters
    ]
    logger.info("Ingestion service running with %d adapters", len(adapters))
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
