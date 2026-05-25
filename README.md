# Market Firehose

A real-time financial news ingestion and streaming pipeline. Pulls articles from multiple sources, enriches them with LLM-extracted metadata (sector, tags, summary), stores them in PostgreSQL, and streams them live over WebSocket.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Ingestion Layer          Processing Layer                       │
│                                                                  │
│  TheNewsAPI ──┐                                                  │
│  RSS feeds  ──┼──► Kafka (raw-articles) ──► LLM Parser          │
│  (add more)  ─┘         │                      │                │
│                          │               ┌──────┴──────┐        │
│                          │               ▼             ▼        │
│                       Storage Layer   PostgreSQL     Redis       │
│                                          │         pub/sub       │
│                                          │             │        │
│                       API Layer       GET /articles  WS /sub    │
└─────────────────────────────────────────────────────────────────┘
```

Data flows through 4 independently scalable layers:

1. **Ingestion** — async feed adapters push raw articles to a Kafka topic. Adding a new source = one new adapter class.
2. **Processing** — Kafka consumers call an LLM (Claude / GPT-4) to extract summary, sector, and named-entity tags. Output is a validated Pydantic event.
3. **Storage** — structured events are upserted into PostgreSQL and published to a Redis channel for real-time subscribers.
4. **API** — FastAPI exposes REST endpoints and a WebSocket stream, documented with auto-generated Swagger UI.

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
- An [Anthropic API key](https://console.anthropic.com/) (or OpenAI key)

### 1. Clone and configure

```bash
git clone https://github.com/your-org/market-firehose.git
cd market-firehose
cp .env.example .env
# Edit .env — fill in THENEWSAPI_KEY and ANTHROPIC_API_KEY (minimum)
```

### 2. Start infrastructure

```bash
docker compose up -d postgres redis kafka
# Wait ~15s for Kafka to be ready, then verify:
docker compose ps
```

### 3. Run database migrations

```bash
pip install -r requirements.txt
alembic upgrade head
```

### 4. Start services

```bash
# Option A — all services via Docker
docker compose up

# Option B — run locally (useful for development)
uvicorn src.api.main:app --reload                # API on :8000
python -m src.ingestion.runner                   # ingestion workers
python -m src.processing.consumer                # LLM processor
```

### 5. Verify

```
GET  http://localhost:8000/health
GET  http://localhost:8000/docs       ← Swagger UI
```

---

## API Reference

All endpoints (except `/health`) require the `X-API-Key` header.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Service health (Kafka, Postgres, Redis) |
| `POST` | `/articles` | Manually ingest a single article |
| `GET` | `/articles` | List/filter articles (sector, source, pagination) |
| `GET` | `/articles/{id}` | Get article by ID |
| `WS` | `/subscribe` | Real-time article stream |

**Filter examples**

```bash
# List Technology articles, page 2
curl -H "X-API-Key: dev-secret-key-1" \
  "http://localhost:8000/articles?sector=Technology&page=2&page_size=10"

# WebSocket stream filtered to Finance
wscat -c "ws://localhost:8000/subscribe?api_key=dev-secret-key-1&sector=Finance"
```

**Swagger UI:** `http://localhost:8000/docs`

---

## Adding a Feed Source

1. Create a new file in [src/ingestion/](src/ingestion/) that subclasses `FeedAdapter`:

```python
# src/ingestion/my_source.py
from src.ingestion.base import FeedAdapter
from src.models.schemas import RawArticle

class MySourceAdapter(FeedAdapter):
    source_name = "my-source"

    async def fetch(self) -> list[RawArticle]:
        # fetch and return articles
        ...
```

2. Register it in [src/ingestion/runner.py](src/ingestion/runner.py):

```python
from src.ingestion.my_source import MySourceAdapter

adapters = [
    ...,
    MySourceAdapter(),
]
```

That's it. The adapter will be polled on `INGESTION_INTERVAL_SECONDS` and its articles will flow through the rest of the pipeline automatically.

---

## Configuration

All configuration is via environment variables. See [.env.example](.env.example) for the full list.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async PostgreSQL DSN |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9094` | Kafka brokers |
| `THENEWSAPI_KEY` | — | TheNewsAPI token |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `LLM_PROVIDER` | `anthropic` | `anthropic` or `openai` |
| `LLM_MODEL` | `claude-sonnet-4-6` | Model ID |
| `API_KEYS` | `dev-secret-key-1` | Comma-separated valid API keys |
| `INGESTION_INTERVAL_SECONDS` | `60` | Feed polling interval |

---

## Development

### Running tests

```bash
pytest
```

### Load testing (Locust)

Targets 100 articles/min throughput:

```bash
locust -f tests/locustfile.py --host http://localhost:8000 \
       --users 20 --spawn-rate 5 --run-time 2m --headless
```

## Contributing

Contributions are welcome.

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Commit your changes
4. Open a pull request

Please keep pull requests focused — one feature or fix per PR.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
