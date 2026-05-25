import logging
from datetime import datetime, timezone
from typing import Optional

import aiohttp

from src.ingestion.base import FeedAdapter
from src.models.schemas import RawArticle

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.thenewsapi.com/v1/news/all"


class TheNewsAPIAdapter(FeedAdapter):
    source_name = "thenewsapi"

    def __init__(
        self,
        api_key: str,
        categories: str = "business,tech,science",
        language: str = "en",
        page_size: int = 25,
    ) -> None:
        self._api_key = api_key
        self._params = {
            "api_token": api_key,
            "categories": categories,
            "language": language,
            "limit": page_size,
        }
        self._seen: set[str] = set()

    async def fetch(self) -> list[RawArticle]:
        async with aiohttp.ClientSession() as session:
            async with session.get(_BASE_URL, params=self._params) as resp:
                resp.raise_for_status()
                data = await resp.json()

        articles: list[RawArticle] = []
        for item in data.get("data", []):
            url: str = item.get("url", "")
            if not url or url in self._seen:
                continue
            self._seen.add(url)
            articles.append(
                RawArticle(
                    source=self.source_name,
                    url=url,
                    title=item.get("title", ""),
                    body=item.get("description") or item.get("snippet"),
                    publisher=item.get("source"),
                    author=None,
                    published_at=_parse_dt(item.get("published_at")),
                    external_id=item.get("uuid"),
                )
            )
        return articles


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None
