import json
import logging

from aiokafka import AIOKafkaProducer

from src.config import settings
from src.models.schemas import RawArticle

logger = logging.getLogger(__name__)


class ArticleProducer:
    def __init__(self) -> None:
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode(),
        )
        await self._producer.start()
        logger.info("Kafka producer started → %s", settings.kafka_bootstrap_servers)

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()

    async def send(self, article: RawArticle) -> None:
        if not self._producer:
            raise RuntimeError("Producer not started")
        payload = article.model_dump(mode="json")
        await self._producer.send_and_wait(settings.kafka_topic_raw, payload)
        logger.debug("Sent article to Kafka: %s", article.url)
