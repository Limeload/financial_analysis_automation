from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ingestion.thenewsapi import TheNewsAPIAdapter

THENEWS_RESPONSE = {
    "data": [
        {
            "uuid": "abc-123",
            "url": "https://example.com/article/1",
            "title": "Markets rally on strong earnings",
            "description": "Stocks surged today...",
            "source": "Reuters",
            "published_at": "2026-05-24T10:00:00Z",
        }
    ]
}


@pytest.mark.asyncio
async def test_thenewsapi_fetch_returns_articles():
    adapter = TheNewsAPIAdapter(api_key="test-key")
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = AsyncMock(return_value=THENEWS_RESPONSE)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        articles = await adapter.fetch()

    assert len(articles) == 1
    assert articles[0].source == "thenewsapi"
    assert articles[0].url == "https://example.com/article/1"
    assert articles[0].external_id == "abc-123"


@pytest.mark.asyncio
async def test_thenewsapi_deduplicates():
    adapter = TheNewsAPIAdapter(api_key="test-key")
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = AsyncMock(return_value=THENEWS_RESPONSE)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        first = await adapter.fetch()
        second = await adapter.fetch()

    assert len(first) == 1
    assert len(second) == 0  # seen set prevents duplicate
