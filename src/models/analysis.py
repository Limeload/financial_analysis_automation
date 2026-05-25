from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)

from src.models.article import Base

EVENT_TYPES = [
    "earnings_release", "merger_acquisition", "product_launch", "regulatory_action",
    "executive_change", "market_movement", "economic_indicator", "analyst_rating",
    "legal_action", "bankruptcy", "ipo", "dividend_change", "share_buyback",
    "partnership", "layoffs", "funding_round", "geopolitical", "other",
]

SENTIMENT_VALUES = ["positive", "negative", "neutral"]


class ArticleAnalysis(Base):
    __tablename__ = "article_analyses"

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(64), nullable=False)
    event_confidence = Column(Numeric(4, 3), nullable=True)
    processed_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("article_id", name="uq_analysis_article"),
        Index("ix_analyses_event_type", "event_type"),
        Index("ix_analyses_processed_at", "processed_at"),
    )


class ArticleCompanySentiment(Base):
    __tablename__ = "article_company_sentiments"

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    analysis_id = Column(Integer, ForeignKey("article_analyses.id", ondelete="CASCADE"), nullable=False)
    company_name = Column(String(255), nullable=False)
    ticker = Column(String(16), nullable=True)
    sentiment = Column(String(16), nullable=False)        # positive | negative | neutral
    sentiment_score = Column(Numeric(4, 3), nullable=True)  # -1.0 to +1.0
    reason = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_acs_ticker", "ticker"),
        Index("ix_acs_sentiment", "sentiment"),
        Index("ix_acs_article_id", "article_id"),
        Index("ix_acs_ticker_article", "ticker", "article_id"),
    )
