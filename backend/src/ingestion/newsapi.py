import logging
from datetime import UTC, datetime

import aiohttp

from src.ingestion.base import FeedAdapter
from src.models.schemas import RawArticle

logger = logging.getLogger(__name__)

_BASE_URL = "https://newsapi.org/v2/everything"


class NewsAPIAdapter(FeedAdapter):
    source_name = "newsapi"

    def __init__(
        self,
        api_key: str,
        query: str = "stock market OR finance OR earnings",
        language: str = "en",
        sort_by: str = "publishedAt",
        page_size: int = 25,
    ) -> None:
        self._api_key = api_key
        self._params = {
            "q": query,
            "language": language,
            "sortBy": sort_by,
            "pageSize": page_size,
            "apiKey": api_key,
        }
        self._seen: set[str] = set()

    async def fetch(self) -> list[RawArticle]:
        async with aiohttp.ClientSession() as session:
            async with session.get(_BASE_URL, params=self._params) as resp:
                resp.raise_for_status()
                data = await resp.json()

        articles: list[RawArticle] = []
        for item in data.get("articles", []):
            url: str = item.get("url", "")
            if not url or url in self._seen:
                continue
            self._seen.add(url)
            articles.append(
                RawArticle(
                    source=self.source_name,
                    url=url,
                    title=item.get("title", ""),
                    body=item.get("content") or item.get("description"),
                    publisher=item.get("source", {}).get("name"),
                    author=item.get("author"),
                    published_at=_parse_dt(item.get("publishedAt")),
                    external_id=None,
                )
            )
        return articles


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(UTC)
    except ValueError:
        return None
