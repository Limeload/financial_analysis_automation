import json
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from src.config import settings
from src.storage.redis_client import RedisSubscriber

router = APIRouter(tags=["realtime"])
logger = logging.getLogger(__name__)


@router.websocket(
    "/subscribe",
    name="Real-time article stream",
)
async def subscribe(
    websocket: WebSocket,
    api_key: str = Query(..., description="Your API key (passed as query param because WebSocket headers are not browser-accessible)"),
    sector: str = Query(None, description="Optional sector filter. Only articles matching this sector are delivered."),
):
    """
    **WebSocket** — subscribe to the live article stream.

    Each message is a JSON object matching the `ArticleResponse` schema.

    **Connect:**
    ```
    ws://localhost:8000/subscribe?api_key=your-key
    ws://localhost:8000/subscribe?api_key=your-key&sector=Technology
    ```

    Closes with code `1008` if the API key is invalid.
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
