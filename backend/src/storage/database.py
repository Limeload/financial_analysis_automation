import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from src.config import settings
from src.models.article import Article, ArticleTag
from src.models.schemas import ParsedArticle

logger = logging.getLogger(__name__)

_engine = create_async_engine(settings.database_url, pool_pre_ping=True)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    async with _session_factory() as session:
        async with session.begin():
            yield session


async def save_article(session: AsyncSession, parsed: ParsedArticle) -> int | None:
    """Upsert an article. Returns the article ID, or None if it was a duplicate."""
    stmt = (
        insert(Article)
        .values(
            source=parsed.source,
            url=parsed.url,
            title=parsed.title,
            body=parsed.body,
            summary=parsed.summary,
            publisher=parsed.publisher,
            author=parsed.author,
            sector=parsed.sector,
            published_at=parsed.published_at,
            external_id=parsed.external_id,
        )
        .on_conflict_do_nothing(constraint="uq_article_source_url")
        .returning(Article.id)
    )
    result = await session.execute(stmt)
    row = result.fetchone()
    if row is None:
        return None  # duplicate — already stored

    article_id: int = row[0]

    if parsed.tags:
        await session.execute(
            insert(ArticleTag)
            .values([{"article_id": article_id, "tag": tag} for tag in parsed.tags])
            .on_conflict_do_nothing(constraint="uq_article_tag")
        )

    return article_id


async def get_articles(
    session: AsyncSession,
    sector: str | None = None,
    source: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Article], int]:
    from sqlalchemy import desc, func

    base = select(Article)
    count_q = select(func.count()).select_from(Article)

    if sector:
        base = base.where(Article.sector == sector)
        count_q = count_q.where(Article.sector == sector)
    if source:
        base = base.where(Article.source == source)
        count_q = count_q.where(Article.source == source)

    total = (await session.execute(count_q)).scalar_one()
    rows = (
        await session.execute(
            base.options(selectinload(Article.tags))
            .order_by(desc(Article.published_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return list(rows), total
