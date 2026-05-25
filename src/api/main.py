import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import articles, websocket
from src.config import settings
from src.models.schemas import HealthResponse

logging.basicConfig(level=settings.log_level)

_DESCRIPTION = """
Market Firehose ingests financial news from multiple sources, enriches each article
with LLM-extracted metadata (sector, named-entity tags, summary), and delivers them
via REST or a live WebSocket stream.

## Authentication

All endpoints except `/health` require an **`X-API-Key`** header:

```
X-API-Key: your-api-key
```

## Real-time streaming

Connect to **`WS /subscribe`** to receive articles as they arrive.
Optional query params: `api_key` (required), `sector` (filter by sector).

## Data flow

```
Feed adapters → Kafka → LLM parser → PostgreSQL + Redis pub/sub → this API
```
"""

_TAGS = [
    {
        "name": "articles",
        "description": "Query and ingest articles. Supports filtering by sector and source with pagination.",
    },
    {
        "name": "realtime",
        "description": "WebSocket endpoint for live article streaming via Redis pub/sub.",
    },
    {
        "name": "ops",
        "description": "Operational endpoints — health checks for Kafka, PostgreSQL, and Redis.",
    },
]

app = FastAPI(
    title="Market Firehose",
    description=_DESCRIPTION,
    version="0.1.0",
    openapi_tags=_TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
    contact={"name": "Market Firehose", "url": "https://github.com/your-org/market-firehose"},
    license_info={"name": "MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(articles.router)
app.include_router(websocket.router)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["ops"],
    summary="Service health check",
    description="Returns the connectivity status of Kafka, PostgreSQL, and Redis. Does not require authentication.",
)
async def health():
    kafka_ok = await _check_kafka()
    pg_ok = await _check_postgres()
    redis_ok = await _check_redis()
    return HealthResponse(
        status="ok" if all([kafka_ok, pg_ok, redis_ok]) else "degraded",
        kafka="ok" if kafka_ok else "error",
        postgres="ok" if pg_ok else "error",
        redis="ok" if redis_ok else "error",
    )


async def _check_kafka() -> bool:
    try:
        from aiokafka.admin import AIOKafkaAdminClient
        client = AIOKafkaAdminClient(bootstrap_servers=settings.kafka_bootstrap_servers)
        await client.start()
        await client.close()
        return True
    except Exception:
        return False


async def _check_postgres() -> bool:
    try:
        from src.storage.database import get_session
        from sqlalchemy import text
        async with get_session() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _check_redis() -> bool:
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        return True
    except Exception:
        return False
