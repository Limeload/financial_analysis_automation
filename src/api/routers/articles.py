from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import require_api_key
from src.models.schemas import ArticleCreate, ArticleListResponse, ArticleResponse, ParsedArticle
from src.storage.database import get_session, get_articles, save_article

router = APIRouter(prefix="/articles", tags=["articles"])


@router.post("", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
async def ingest_article(
    body: ArticleCreate,
    _: str = Depends(require_api_key),
):
    """Manually ingest a single article (bypasses Kafka, goes straight to DB)."""
    parsed = ParsedArticle(**body.model_dump())
    async with get_session() as session:
        article_id = await save_article(session, parsed)
    if article_id is None:
        raise HTTPException(status_code=409, detail="Article already exists")
    return ArticleResponse(id=article_id, **body.model_dump(), created_at=__import__("datetime").datetime.utcnow())


@router.get("", response_model=ArticleListResponse)
async def list_articles(
    sector: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: str = Depends(require_api_key),
):
    async with get_session() as session:
        articles, total = await get_articles(session, sector=sector, source=source, page=page, page_size=page_size)

    return ArticleListResponse(
        items=[ArticleResponse.from_orm_with_tags(a) for a in articles],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: int,
    _: str = Depends(require_api_key),
):
    from sqlalchemy import select
    from src.models.article import Article
    async with get_session() as session:
        result = await session.execute(
            select(Article).where(Article.id == article_id)
        )
        article = result.scalar_one_or_none()
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return ArticleResponse.from_orm_with_tags(article)
