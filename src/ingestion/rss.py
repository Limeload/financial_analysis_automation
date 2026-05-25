import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

import aiohttp
import feedparser

from src.ingestion.base import FeedAdapter
from src.models.schemas import RawArticle

logger = logging.getLogger(__name__)


class RSSAdapter(FeedAdapter):
    """Generic RSS / Atom feed adapter. Pass any public feed URL."""

    source_name = "rss"

    def __init__(self, feed_url: str, source_name: Optional[str] = None) -> None:
        self._feed_url = feed_url
        if source_name:
            self.source_name = source_name
        self._seen: set[str] = set()

    async def fetch(self) -> list[RawArticle]:
        async with aiohttp.ClientSession() as session:
            async with session.get(self._feed_url) as resp:
                content = await resp.read()

        feed = feedparser.parse(content)
        articles: list[RawArticle] = []

        for entry in feed.entries:
            url: str = entry.get("link", "")
            if not url or url in self._seen:
                continue
            self._seen.add(url)

            summary = entry.get("summary") or entry.get("description")
            body = _strip_html(summary) if summary else None

            articles.append(
                RawArticle(
                    source=self.source_name,
                    url=url,
                    title=entry.get("title", ""),
                    body=body,
                    publisher=feed.feed.get("title"),
                    author=_get_author(entry),
                    published_at=_parse_dt(entry),
                    external_id=entry.get("id"),
                )
            )
        return articles


def _get_author(entry) -> Optional[str]:
    if "author" in entry:
        return entry.author
    authors = entry.get("authors", [])
    if authors:
        return authors[0].get("name")
    return None


def _parse_dt(entry) -> Optional[datetime]:
    for field in ("published_parsed", "updated_parsed"):
        value = entry.get(field)
        if value:
            import time
            return datetime.fromtimestamp(time.mktime(value), tz=timezone.utc)
    return None


def _strip_html(text: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", text).strip()
