"""stocks and stock_metrics tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stocks",
        sa.Column("ticker", sa.String(10), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("exchange", sa.String(16), nullable=True),
        sa.Column("sector", sa.String(128), nullable=True),
        sa.Column("industry", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("website", sa.String(255), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_stocks_sector", "stocks", ["sector"])
    op.create_index("ix_stocks_exchange", "stocks", ["exchange"])

    op.create_table(
        "stock_metrics",
        sa.Column("ticker", sa.String(10),
                  sa.ForeignKey("stocks.ticker", ondelete="CASCADE"), primary_key=True),
        sa.Column("market_cap", sa.BigInteger(), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("avg_volume", sa.BigInteger(), nullable=True),
        sa.Column("pe_ratio", sa.Numeric(10, 2), nullable=True),
        sa.Column("dividend_yield", sa.Numeric(6, 4), nullable=True),
        sa.Column("week52_high", sa.Numeric(12, 2), nullable=True),
        sa.Column("week52_low", sa.Numeric(12, 2), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_stock_metrics_market_cap", "stock_metrics", ["market_cap"])
    op.create_index("ix_stock_metrics_volume", "stock_metrics", ["volume"])


def downgrade() -> None:
    op.drop_table("stock_metrics")
    op.drop_table("stocks")
