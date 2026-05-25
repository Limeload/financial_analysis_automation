import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status

from src.config import settings
from src.storage.redis_client import RedisSubscriber

router = APIRouter(tags=["realtime"])
logger = logging.getLogger(__name__)


@router.websocket("/subscribe")
async def subscribe(
    websocket: WebSocket,
    api_key: str = Query(...),
    sector: str = Query(None),
):
    """Stream articles in real-time via WebSocket.

    Connect with ?api_key=<your-key>. Optionally filter by ?sector=Technology.
    """
    if api_key not in settings.api_key_set:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    subscriber = RedisSubscriber()
    await subscriber.connect()
    logger.info("WebSocket client connected (sector=%s)", sector)

    try:
        async for article in subscriber.subscribe():
            if sector and article.get("sector") != sector:
                continue
            await websocket.send_text(json.dumps(article))
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    finally:
        await subscriber.close()
