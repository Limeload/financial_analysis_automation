import logging
from datetime import UTC, datetime

import aiohttp

from src.ingestion.base import FeedAdapter
from src.models.schemas import RawArticle

logger = logging.getLogger(__name__)

_BASE_URL = "http://api.mediastack.com/v1/news"


class MediastackAdapter(FeedAdapter):
    source_name = "mediastack"

    def __init__(
        self,
        api_key: str,
        categories: str = "business,technology",
        languages: str = "en",
        limit: int = 25,
    ) -> None:
        self._params = {
            "access_key": api_key,
            "categories": categories,
            "languages": languages,
            "limit": limit,
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
                    body=item.get("description"),
                    publisher=item.get("source"),
                    author=item.get("author"),
                    published_at=_parse_dt(item.get("published_at")),
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
