# MarketPulse

[![CI](https://github.com/your-org/marketpulse/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/marketpulse/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

A real-time financial news intelligence platform. Ingests articles from multiple sources, enriches them with LLM-extracted metadata, performs per-company sentiment analysis and event classification, and delivers everything via REST or live WebSocket stream.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  Ingestion Layer              Processing Layer                        │
│                                                                       │
│  TheNewsAPI ──┐                                                       │
│  RSS feeds  ──┼──► Kafka (raw-articles) ──► Enrichment (LLM)        │
│  (add more) ──┘         │                      │                     │
│                          │               ┌──────┴──────┐             │
│                          │               ▼             ▼             │
│                       Storage Layer   PostgreSQL     Redis pub/sub   │
│                                          │             │             │
│                          ┌───────────────┘             │             │
│                          ▼                             │             │
│  Analysis Layer   Kafka (processed-articles)           │             │
│                          │                             │             │
│                          ▼                             ▼             │
│                   Market Analysis (LLM) ──► Redis (article-analyses) │
│                   Companies + Sentiment                │             │
│                   Event Classification                 │             │
│                                                        │             │
│  API Layer     REST /articles  /analysis  /stocks   WS /stream      │
└──────────────────────────────────────────────────────────────────────┘
```

Data flows through 4 independently scalable layers:

1. **Ingestion** — async feed adapters push raw articles to Kafka. Adding a source = one new adapter class.
2. **Processing** — Kafka consumers call an LLM to extract summary, sector, and tags. Structured events written to PostgreSQL + Redis.
3. **Analysis** — second LLM pass per article: identifies mentioned companies, scores sentiment (−1 to +1), and classifies 18 event types. Runs concurrently at scale with prompt caching.
4. **API** — FastAPI exposes REST, a stock screener + NL search, and two real-time WebSocket streams.

---

## Tech Stack

| Concern | Choice |
|---|---|
| Message queue | Apache Kafka (KRaft, via Bitnami) |
| API framework | FastAPI + Pydantic v2 |
| Primary database | PostgreSQL 16 |
| Real-time cache | Redis 7 pub/sub |
| LLM | Anthropic Claude (primary) / OpenAI GPT-4 (fallback) |
| News feeds | TheNewsAPI + RSS |
| Stock data | Yahoo Finance (yfinance) + NASDAQ screener |
| Async runtime | asyncio / aiohttp / aiokafka |
| Containerization | Docker + Compose |
| Migrations | Alembic |
| Testing | pytest + Locust |

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.12+
- A [TheNewsAPI](https://www.thenewsapi.com/) token (free tier works)
- An [Anthropic API key](https://console.anthropic.com/)

### 1. Clone and configure

```bash
git clone https://github.com/your-org/marketpulse.git
cd marketpulse
cp .env.example .env
# Edit .env — fill in THENEWSAPI_KEY and ANTHROPIC_API_KEY at minimum
```

### 2. Start infrastructure

```bash
make up
# or: docker compose up -d postgres redis kafka
```

### 3. Run database migrations

```bash
make install
make migrate
```

### 4. Start services

```bash
# All services via Docker:
docker compose up

# Or individually for local development:
make dev          # API on :8000
make run-ingest   # ingestion workers
make run-process  # LLM processor
make run-analysis # market analysis
```

### 5. Verify

```bash
curl http://localhost:8000/health
# Open http://localhost:8000/docs for the full Swagger UI
```

---

## API Reference

All endpoints except `/health` require the `X-API-Key` header.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Dependency health check |
| `POST` | `/articles` | Manually ingest an article |
| `GET` | `/articles` | List / filter articles |
| `GET` | `/articles/{id}` | Get article by ID |
| `WS` | `/subscribe` | Real-time article stream |
| `GET` | `/analysis/articles/{id}` | Event type + per-company sentiment |
| `GET` | `/analysis/companies/{ticker}/sentiment` | Sentiment feed for a ticker |
| `GET` | `/analysis/companies/{ticker}/summary` | Aggregated sentiment score |
| `GET` | `/analysis/events` | Browse events by type |
| `WS` | `/analysis/stream` | Live analysis stream |
| `GET` | `/stocks/search?q=...` | Natural-language stock search |
| `GET` | `/stocks` | Metric-based stock screener |
| `GET` | `/stocks/{ticker}` | Stock detail + metrics |
| `POST` | `/stocks/refresh` | Trigger NYSE universe refresh |

**Swagger UI:** `http://localhost:8000/docs`  
**ReDoc:** `http://localhost:8000/redoc`

---

## Adding a Feed Source

Create a subclass of `FeedAdapter` and register it in the runner — that's all:

```python
# src/ingestion/my_source.py
from src.ingestion.base import FeedAdapter
from src.models.schemas import RawArticle

class MySourceAdapter(FeedAdapter):
    source_name = "my-source"

    async def fetch(self) -> list[RawArticle]:
        ...  # fetch and return articles
```

```python
# src/ingestion/runner.py  — add one line
from src.ingestion.my_source import MySourceAdapter
adapters = [..., MySourceAdapter()]
```

---

## Configuration

All config is via environment variables. See [.env.example](.env.example).

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async PostgreSQL DSN |
| `REDIS_URL` | `redis://localhost:6379` | Redis URL |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9094` | Kafka brokers |
| `THENEWSAPI_KEY` | — | TheNewsAPI token |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `LLM_PROVIDER` | `anthropic` | `anthropic` or `openai` |
| `LLM_MODEL` | `claude-sonnet-4-6` | Model ID |
| `API_KEYS` | `dev-secret-key-1` | Comma-separated valid API keys |
| `ANALYSIS_CONCURRENCY` | `20` | Concurrent LLM calls per analysis worker |

---

## Development

```bash
make install    # pip install -r requirements.txt
make test       # pytest
make lint       # ruff check
make up         # start infra (Kafka, Redis, Postgres)
make migrate    # alembic upgrade head
make dev        # uvicorn with --reload
```

### Load testing

```bash
make load-test
# locust -f tests/locustfile.py --host http://localhost:8000 \
#        --users 20 --spawn-rate 5 --run-time 2m --headless
```

### Project structure

```
src/
├── config.py               # Pydantic-settings
├── models/
│   ├── article.py          # SQLAlchemy ORM — articles, tags, api_keys
│   ├── analysis.py         # SQLAlchemy ORM — analyses, company sentiments
│   ├── stock.py            # SQLAlchemy ORM — stocks, metrics
│   └── schemas.py          # Pydantic v2 request/response schemas
├── ingestion/
│   ├── base.py             # FeedAdapter ABC
│   ├── thenewsapi.py       # TheNewsAPI adapter
│   ├── rss.py              # Generic RSS/Atom adapter
│   ├── kafka_producer.py   # aiokafka producer wrapper
│   └── runner.py           # Ingestion service entry point
├── processing/
│   ├── prompts.py          # Article enrichment prompt
│   ├── llm_parser.py       # Enrichment LLM wrapper
│   └── consumer.py         # Kafka consumer → enrichment → DB + Redis
├── analysis/
│   ├── prompts.py          # Market analysis prompt (prompt-cached)
│   ├── processor.py        # Analysis LLM wrapper (semaphore + retry)
│   ├── store.py            # Persist analysis + publish to Redis
│   └── consumer.py         # High-throughput Kafka consumer
├── research/
│   ├── fetcher.py          # NASDAQ screener + yfinance enrichment
│   ├── nl_search.py        # NL query → Claude → stock results
│   ├── screener.py         # Metric-based DB screener
│   └── runner.py           # Universe + metrics refresh service
└── api/
    ├── main.py             # FastAPI app
    ├── dependencies.py     # API key auth
    └── routers/
        ├── articles.py     # /articles
        ├── websocket.py    # WS /subscribe
        ├── analysis.py     # /analysis
        └── stocks.py       # /stocks
```

---

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Make your changes and add tests
4. Open a pull request

---

## License

MIT License — see [LICENSE](LICENSE) for details.
