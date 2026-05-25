from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl, Field


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
    source: str
    url: str
    title: str
    body: Optional[str] = None
    publisher: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None


class ArticleResponse(BaseModel):
    id: int
    source: str
    url: str
    title: str
    summary: Optional[str] = None
    publisher: Optional[str] = None
    author: Optional[str] = None
    sector: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    published_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}

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
    total: int
    page: int
    page_size: int


class HealthResponse(BaseModel):
    status: str
    kafka: str
    postgres: str
    redis: str
