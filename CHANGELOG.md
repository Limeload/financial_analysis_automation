# Changelog

All notable changes to MarketPulse are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
MarketPulse uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.1.0] — 2026-05-24

### Added

**Ingestion layer**
- `FeedAdapter` base class with polling loop and in-process deduplication
- `TheNewsAPIAdapter` — TheNewsAPI integration (business, tech, science categories)
- `RSSAdapter` — generic RSS/Atom adapter; accepts any public feed URL
- `ArticleProducer` — aiokafka producer wrapper for `raw-articles` topic

**Processing layer**
- `LLMParser` — Anthropic Claude primary / OpenAI fallback; extracts summary, sector, named-entity tags
- Kafka consumer with Redis pub/sub publish on store
- Downstream forwarding to `processed-articles` topic for analysis pipeline

**Analysis layer**
- `ArticleAnalyzer` — single Claude call extracts companies, per-company sentiment (−1 to +1), and event type
- Prompt caching on the static system prompt (~90% token savings at steady state)
- High-throughput consumer: `getmany()` + `asyncio.gather()` + `Semaphore(20)`; scales horizontally via Kafka consumer groups
- 18 event types: `earnings_release`, `merger_acquisition`, `product_launch`, `regulatory_action`, `executive_change`, `market_movement`, `economic_indicator`, `analyst_rating`, `legal_action`, `bankruptcy`, `ipo`, `dividend_change`, `share_buyback`, `partnership`, `layoffs`, `funding_round`, `geopolitical`, `other`

**Research automation**
- `NLSearchEngine` — natural-language queries via Claude (e.g. "companies that build data centers")
- `Screener` — filter NYSE stocks by market cap, volume, price, P/E, dividend yield, sector, industry
- NASDAQ screener API integration for full NYSE universe seeding
- yfinance per-ticker enrichment with bounded async concurrency
- Background runner: universe refresh (24 h) + metrics refresh (1 h)

**API (FastAPI)**
- `POST /articles`, `GET /articles`, `GET /articles/{id}`
- `WS /subscribe` — real-time article stream, optional sector filter
- `GET /analysis/articles/{id}`, `GET /analysis/companies/{ticker}/sentiment`
- `GET /analysis/companies/{ticker}/summary`, `GET /analysis/events`
- `WS /analysis/stream` — live analysis stream, filter by ticker or event type
- `GET /stocks/search`, `GET /stocks`, `GET /stocks/{ticker}`, `POST /stocks/refresh`
- `GET /health`
- API key authentication via `X-API-Key` header
- Swagger UI at `/docs`, ReDoc at `/redoc`

**Infrastructure**
- Docker Compose: Kafka (KRaft), Redis 7, PostgreSQL 16, api, ingestion, processor, analysis (×2 replicas), research services
- Alembic migrations: articles, stocks, analysis tables
- pytest suite with async fixtures and mocked external services
- Locust load test targeting 100 articles/min

[Unreleased]: https://github.com/your-org/marketpulse/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/your-org/marketpulse/releases/tag/v0.1.0
