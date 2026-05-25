import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import articles, websocket
from src.config import settings
from src.models.schemas import HealthResponse

logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title="Market Firehose",
    description="Real-time financial news ingestion and streaming API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(articles.router)
app.include_router(websocket.router)


@app.get("/health", response_model=HealthResponse, tags=["ops"])
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
