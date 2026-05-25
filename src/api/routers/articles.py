from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import require_api_key
from src.models.schemas import ArticleCreate, ArticleListResponse, ArticleResponse, ParsedArticle, SECTORS
from src.storage.database import get_session, get_articles, save_article

router = APIRouter(prefix="/articles", tags=["articles"])

_AUTH_ERR = {401: {"description": "Missing or invalid `X-API-Key` header"}}
_NOT_FOUND_ERR = {404: {"description": "Article not found"}}
_CONFLICT_ERR = {409: {"description": "An article with the same source + URL already exists"}}


@router.post(
    "",
    response_model=ArticleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest an article",
    description=(
        "Directly write a single article into the database, bypassing Kafka. "
        "Useful for testing or one-off imports. The LLM enrichment step is **skipped** — "
        "`summary`, `sector`, and `tags` will be empty until the processing worker picks it up."
    ),
    responses={**_AUTH_ERR, **_CONFLICT_ERR},
)
async def ingest_article(
    body: ArticleCreate,
    _: str = Depends(require_api_key),
):
    parsed = ParsedArticle(**body.model_dump())
    async with get_session() as session:
        article_id = await save_article(session, parsed)
    if article_id is None:
        raise HTTPException(status_code=409, detail="Article already exists")
    return ArticleResponse(id=article_id, **body.model_dump(), created_at=__import__("datetime").datetime.utcnow())


@router.get(
    "",
    response_model=ArticleListResponse,
    summary="List articles",
    description=(
        "Return a paginated list of enriched articles. "
        f"Filter by **sector** (one of: `{'`, `'.join(SECTORS)}`) "
        "or by **source** (e.g. `thenewsapi`, `bloomberg`, `reuters`). "
        "Results are ordered by `published_at` descending."
    ),
    responses=_AUTH_ERR,
)
async def list_articles(
    sector: Optional[str] = Query(None, description="Filter by sector", examples=["Technology", "Finance"]),
    source: Optional[str] = Query(None, description="Filter by feed source identifier", examples=["thenewsapi", "bloomberg"]),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
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


@router.get(
    "/{article_id}",
    response_model=ArticleResponse,
    summary="Get article by ID",
    description="Fetch a single article and its tags by its internal database ID.",
    responses={**_AUTH_ERR, **_NOT_FOUND_ERR},
)
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
