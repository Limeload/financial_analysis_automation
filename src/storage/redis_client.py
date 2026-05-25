import json
import logging
from collections.abc import AsyncIterator

import redis.asyncio as aioredis

from src.config import settings
from src.models.schemas import ParsedArticle

logger = logging.getLogger(__name__)

CHANNEL = "articles"


class RedisPublisher:
    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        logger.info("Redis publisher connected")

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()

    async def publish(self, article: ParsedArticle, article_id: int) -> None:
        if not self._redis:
            raise RuntimeError("Not connected")
        payload = article.model_dump(mode="json")
        payload["id"] = article_id
        await self._redis.publish(CHANNEL, json.dumps(payload))


class RedisSubscriber:
    """Used by the WebSocket endpoint to stream real-time articles."""

    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()

    async def subscribe(self) -> AsyncIterator[dict]:
        if not self._redis:
            raise RuntimeError("Not connected")
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(CHANNEL)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield json.loads(message["data"])
        finally:
            await pubsub.unsubscribe(CHANNEL)
            await pubsub.aclose()
