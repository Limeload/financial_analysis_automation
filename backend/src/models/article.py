from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    external_id = Column(String(255), nullable=True)   # source-assigned ID
    source = Column(String(64), nullable=False)         # thenewsapi | rss | ...
    url = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    body = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)               # LLM-generated
    publisher = Column(String(255), nullable=True)
    author = Column(String(255), nullable=True)
    sector = Column(String(128), nullable=True)         # LLM-classified
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tags = relationship("ArticleTag", back_populates="article", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("source", "url", name="uq_article_source_url"),
        Index("ix_articles_sector", "sector"),
        Index("ix_articles_published_at", "published_at"),
        Index("ix_articles_created_at", "created_at"),
    )


class ArticleTag(Base):
    __tablename__ = "article_tags"

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    tag = Column(String(128), nullable=False)

    article = relationship("Article", back_populates="tags")

    __table_args__ = (
        UniqueConstraint("article_id", "tag", name="uq_article_tag"),
        Index("ix_article_tags_tag", "tag"),
    )


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True)
    key_hash = Column(String(64), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
