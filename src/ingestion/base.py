import abc
import asyncio
import logging
from src.models.schemas import RawArticle

logger = logging.getLogger(__name__)


class FeedAdapter(abc.ABC):
    """Base class for all feed adapters. Implement `fetch` to return a list of RawArticles."""

    source_name: str = "unknown"

    @abc.abstractmethod
    async def fetch(self) -> list[RawArticle]:
        """Fetch latest articles from the source. Returns deduplicated raw articles."""

    async def run_forever(self, producer, interval_seconds: int = 60) -> None:
        """Poll the source on a fixed interval and push articles to Kafka."""
        logger.info("Starting adapter %s (interval=%ds)", self.source_name, interval_seconds)
        while True:
            try:
                articles = await self.fetch()
                logger.info("%s fetched %d articles", self.source_name, len(articles))
                for article in articles:
                    await producer.send(article)
            except Exception:
                logger.exception("Error in adapter %s", self.source_name)
            await asyncio.sleep(interval_seconds)
