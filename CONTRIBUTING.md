# Contributing to MarketPulse

Thank you for your interest in contributing! This document covers everything you need
to get your environment up, understand the codebase, and get a pull request merged.

---

## Table of Contents

- [Development setup](#development-setup)
- [Running tests](#running-tests)
- [Code style](#code-style)
- [Project conventions](#project-conventions)
- [How to add a feed adapter](#how-to-add-a-feed-adapter)
- [How to add an LLM provider](#how-to-add-an-llm-provider)
- [Pull request checklist](#pull-request-checklist)

---

## Development setup

```bash
git clone https://github.com/your-org/marketpulse.git
cd marketpulse

# Create a virtual environment
python -m venv .venv && source .venv/bin/activate

# Install all dependencies (runtime + dev)
make install

# Copy env and fill in at least ANTHROPIC_API_KEY
cp .env.example .env

# Start infrastructure
make up

# Apply migrations
make migrate

# Start the API
make dev
```

---

## Running tests

```bash
make test          # full suite
pytest tests/test_api.py -v          # one file
pytest -k "sentiment" -v             # by keyword
```

Tests mock all external services (Kafka, Postgres, Redis, LLM APIs) — no live
connections needed. Keep it that way: do not add tests that require running infrastructure.

---

## Code style

MarketPulse uses [Ruff](https://docs.astral.sh/ruff/) for linting.

```bash
make lint          # check
make lint-fix      # auto-fix
```

A few house rules:
- No comments explaining *what* code does — good names do that.
- Comments only for non-obvious *why*: a hidden constraint, an API quirk, a workaround.
- No docstrings on trivial functions. A one-liner on a public class or module is fine.
- No backwards-compat shims or `# TODO` left in merged PRs.

---

## Project conventions

### Async everywhere

All I/O is `async`. Do not use synchronous `requests`, `psycopg2`, or blocking file
reads inside async functions. Use `asyncio.to_thread()` for unavoidable sync libraries
(e.g. `yfinance`).

### LLM calls

- Always use the `tenacity` retry decorator (`@retry`) on LLM call methods.
- For Anthropic, pass the system prompt as a list with `cache_control: ephemeral` so
  the prompt is cached across calls. See [src/analysis/processor.py](src/analysis/processor.py).
- LLM responses must go through `_safe_parse()` — never `json.loads()` directly.

### Kafka topics

| Topic | Producer | Consumer |
|---|---|---|
| `raw-articles` | ingestion adapters | processing consumer |
| `processed-articles` | processing consumer | analysis consumer |

Add new topics to `src/config.py` as typed fields, not bare strings.

### Database

- All DB access is async SQLAlchemy (`asyncpg` driver).
- Use `insert().on_conflict_do_nothing()` / `on_conflict_do_update()` for upserts —
  never check-then-insert.
- Add a migration for every schema change: `alembic revision --autogenerate -m "description"`.

---

## How to add a feed adapter

1. Create `src/ingestion/<name>.py` subclassing `FeedAdapter`:

```python
from src.ingestion.base import FeedAdapter
from src.models.schemas import RawArticle

class MyAdapter(FeedAdapter):
    source_name = "my-source"   # appears in the `source` column

    async def fetch(self) -> list[RawArticle]:
        # Pull latest articles, return RawArticle list
        # Use self._seen: set[str] for in-process URL deduplication
        ...
```

2. Register in [src/ingestion/runner.py](src/ingestion/runner.py):

```python
from src.ingestion.my_adapter import MyAdapter
adapters = [..., MyAdapter(api_key=settings.my_source_key)]
```

3. Add any new API key to `src/config.py` and `.env.example`.

4. Add a unit test in `tests/test_ingestion.py` that mocks the HTTP call.

---

## How to add an LLM provider

Both `LLMParser` (processing) and `ArticleAnalyzer` (analysis) resolve the provider
at construction time via `settings.llm_provider`. To add a new provider:

1. Add a `_call_<provider>` method to each class.
2. Wire it in `__init__` with an `elif` branch.
3. Add the API key field to `src/config.py` and `.env.example`.

---

## Pull request checklist

- [ ] Tests pass: `make test`
- [ ] No lint errors: `make lint`
- [ ] New behaviour has a test
- [ ] Schema changes have an Alembic migration
- [ ] `.env.example` updated if new env vars added
- [ ] PR description explains *why*, not just *what*
