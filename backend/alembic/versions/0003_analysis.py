"""article_analyses and article_company_sentiments tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "article_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("article_id", sa.Integer(),
                  sa.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("event_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("article_id", name="uq_analysis_article"),
    )
    op.create_index("ix_analyses_event_type", "article_analyses", ["event_type"])
    op.create_index("ix_analyses_processed_at", "article_analyses", ["processed_at"])

    op.create_table(
        "article_company_sentiments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("article_id", sa.Integer(),
                  sa.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("analysis_id", sa.Integer(),
                  sa.ForeignKey("article_analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("ticker", sa.String(16), nullable=True),
        sa.Column("sentiment", sa.String(16), nullable=False),
        sa.Column("sentiment_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_acs_ticker", "article_company_sentiments", ["ticker"])
    op.create_index("ix_acs_sentiment", "article_company_sentiments", ["sentiment"])
    op.create_index("ix_acs_article_id", "article_company_sentiments", ["article_id"])
    op.create_index("ix_acs_ticker_article", "article_company_sentiments", ["ticker", "article_id"])


def downgrade() -> None:
    op.drop_table("article_company_sentiments")
    op.drop_table("article_analyses")
