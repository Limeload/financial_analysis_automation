from datetime import datetime
from sqlalchemy import (
    Column, String, Text, DateTime, BigInteger, Numeric, Index,
    ForeignKey, func,
)
from src.models.article import Base


class Stock(Base):
    __tablename__ = "stocks"

    ticker = Column(String(10), primary_key=True)
    name = Column(Text, nullable=False)
    exchange = Column(String(16), nullable=True)   # NYSE, NMS, etc.
    sector = Column(String(128), nullable=True)
    industry = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    website = Column(String(255), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_stocks_sector", "sector"),
        Index("ix_stocks_exchange", "exchange"),
    )


class StockMetrics(Base):
    __tablename__ = "stock_metrics"

    ticker = Column(String(10), ForeignKey("stocks.ticker", ondelete="CASCADE"), primary_key=True)
    market_cap = Column(BigInteger, nullable=True)
    price = Column(Numeric(12, 2), nullable=True)
    volume = Column(BigInteger, nullable=True)
    avg_volume = Column(BigInteger, nullable=True)
    pe_ratio = Column(Numeric(10, 2), nullable=True)
    dividend_yield = Column(Numeric(6, 4), nullable=True)
    week52_high = Column(Numeric(12, 2), nullable=True)
    week52_low = Column(Numeric(12, 2), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_stock_metrics_market_cap", "market_cap"),
        Index("ix_stock_metrics_volume", "volume"),
    )
