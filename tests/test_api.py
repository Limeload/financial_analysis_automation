import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone


def _mock_article(article_id: int = 1):
    a = MagicMock()
    a.id = article_id
    a.source = "thenewsapi"
    a.url = f"https://example.com/{article_id}"
    a.title = f"Test Article {article_id}"
    a.summary = "A summary."
    a.publisher = "Reuters"
    a.author = "Jane Doe"
    a.sector = "Technology"
    a.published_at = datetime(2026, 5, 24, tzinfo=timezone.utc)
    a.created_at = datetime(2026, 5, 24, tzinfo=timezone.utc)
    a.tags = []
    return a


@pytest.mark.asyncio
async def test_health_endpoint(client):
    with (
        patch("src.api.main._check_kafka", AsyncMock(return_value=True)),
        patch("src.api.main._check_postgres", AsyncMock(return_value=True)),
        patch("src.api.main._check_redis", AsyncMock(return_value=True)),
    ):
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_list_articles_requires_auth(client):
    from httpx import AsyncClient, ASGITransport
    from src.api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
        resp = await anon.get("/articles")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_articles(client):
    article = _mock_article()
    with patch("src.api.routers.articles.get_articles", AsyncMock(return_value=([article], 1))):
        with patch("src.api.routers.articles.get_session") as mock_ctx:
            mock_ctx.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_ctx.return_value.__aexit__ = AsyncMock(return_value=None)
            resp = await client.get("/articles")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_get_article_not_found(client):
    with patch("src.api.routers.articles.get_session") as mock_ctx:
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.return_value.__aexit__ = AsyncMock(return_value=None)
        resp = await client.get("/articles/9999")
    assert resp.status_code == 404
