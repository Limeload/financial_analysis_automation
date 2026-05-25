from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

_EXAMPLE_ARTICLE = {
    "id": 42,
    "source": "thenewsapi",
    "url": "https://reuters.com/markets/us/apple-q2-earnings-2026-05-24",
    "title": "Apple posts record Q2 earnings on iPhone and services growth",
    "summary": "Apple reported record second-quarter earnings driven by strong iPhone sales and continued growth in its services segment.",
    "publisher": "Reuters",
    "author": "Jane Doe",
    "sector": "Technology",
    "tags": ["Apple", "AAPL", "earnings", "iPhone", "services"],
    "published_at": "2026-05-24T10:00:00Z",
    "created_at": "2026-05-24T10:01:23Z",
}

SECTORS = [
    "Technology", "Finance", "Healthcare", "Energy", "Consumer",
    "Industrials", "Real Estate", "Materials", "Utilities", "Telecom",
    "Government", "Other",
]


# ── Raw article off the wire ─────────────────────────────────────────────────

class RawArticle(BaseModel):
    source: str
    url: str
    title: str
    body: Optional[str] = None
    publisher: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    external_id: Optional[str] = None


# ── LLM-enriched article ─────────────────────────────────────────────────────

class ParsedArticle(RawArticle):
    summary: Optional[str] = None
    sector: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


# ── API request / response ───────────────────────────────────────────────────

class ArticleCreate(BaseModel):
    source: str = Field(description="Feed source identifier, e.g. `thenewsapi`, `rss`, `bloomberg`")
    url: str = Field(description="Canonical article URL — used for deduplication")
    title: str = Field(description="Article headline")
    body: Optional[str] = Field(None, description="Full article text or excerpt")
    publisher: Optional[str] = Field(None, description="Publishing outlet name")
    author: Optional[str] = Field(None, description="Byline author name")
    published_at: Optional[datetime] = Field(None, description="Original publication timestamp (ISO 8601)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "source": "thenewsapi",
                "url": "https://reuters.com/markets/us/apple-q2-earnings-2026-05-24",
                "title": "Apple posts record Q2 earnings on iPhone and services growth",
                "body": "Apple Inc. reported record second-quarter earnings on Monday...",
                "publisher": "Reuters",
                "author": "Jane Doe",
                "published_at": "2026-05-24T10:00:00Z",
            }
        }
    }


class ArticleResponse(BaseModel):
    id: int = Field(description="Internal article ID")
    source: str = Field(description="Feed source that produced this article")
    url: str = Field(description="Canonical article URL")
    title: str = Field(description="Article headline")
    summary: Optional[str] = Field(None, description="LLM-generated 2-3 sentence summary")
    publisher: Optional[str] = Field(None, description="Publishing outlet")
    author: Optional[str] = Field(None, description="Byline author")
    sector: Optional[str] = Field(None, description=f"LLM-classified sector. One of: {', '.join(SECTORS)}")
    tags: list[str] = Field(default_factory=list, description="LLM-extracted named entities and keywords")
    published_at: Optional[datetime] = Field(None, description="Original publication timestamp")
    created_at: datetime = Field(description="Timestamp when the article entered the pipeline")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {"example": _EXAMPLE_ARTICLE},
    }

    @classmethod
    def from_orm_with_tags(cls, article) -> "ArticleResponse":
        return cls(
            **{c: getattr(article, c) for c in [
                "id", "source", "url", "title", "summary",
                "publisher", "author", "sector", "published_at", "created_at",
            ]},
            tags=[t.tag for t in article.tags],
        )


class ArticleListResponse(BaseModel):
    items: list[ArticleResponse]
    total: int = Field(description="Total matching articles (across all pages)")
    page: int = Field(description="Current page number (1-indexed)")
    page_size: int = Field(description="Number of items per page")

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [_EXAMPLE_ARTICLE],
                "total": 1,
                "page": 1,
                "page_size": 20,
            }
        }
    }


class HealthResponse(BaseModel):
    status: str = Field(description="`ok` if all dependencies are healthy, `degraded` otherwise")
    kafka: str = Field(description="`ok` or `error`")
    postgres: str = Field(description="`ok` or `error`")
    redis: str = Field(description="`ok` or `error`")

    model_config = {
        "json_schema_extra": {
            "example": {"status": "ok", "kafka": "ok", "postgres": "ok", "redis": "ok"}
        }
    }
