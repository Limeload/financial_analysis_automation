.PHONY: help install up down migrate dev \
        run-ingest run-process run-analysis run-research \
        test lint lint-fix load-test clean

help:
	@echo "MarketPulse — development commands"
	@echo ""
	@echo "  make install      Install Python dependencies"
	@echo "  make up           Start Kafka, Redis, PostgreSQL"
	@echo "  make down         Stop all Docker services"
	@echo "  make migrate      Run Alembic migrations"
	@echo "  make dev          Start API with hot-reload on :8000"
	@echo "  make run-ingest   Start ingestion service"
	@echo "  make run-process  Start processing (LLM enrichment) service"
	@echo "  make run-analysis Start market analysis service"
	@echo "  make run-research Start stock universe refresh service"
	@echo "  make test         Run pytest suite"
	@echo "  make lint         Ruff lint check"
	@echo "  make lint-fix     Ruff auto-fix"
	@echo "  make load-test    Locust load test (requires running API)"
	@echo "  make clean        Remove __pycache__ and .pytest_cache"

install:
	pip install -r requirements.txt

up:
	docker compose up -d postgres redis kafka
	@echo "Waiting for services to be ready…"
	@sleep 5

down:
	docker compose down

migrate:
	alembic upgrade head

dev:
	uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

run-ingest:
	python -m src.ingestion.runner

run-process:
	python -m src.processing.consumer

run-analysis:
	python -m src.analysis.consumer

run-research:
	python -m src.research.runner

test:
	pytest --tb=short

lint:
	ruff check src/ tests/

lint-fix:
	ruff check --fix src/ tests/

load-test:
	locust -f tests/locustfile.py --host http://localhost:8000 \
	       --users 20 --spawn-rate 5 --run-time 2m --headless

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	rm -rf .pytest_cache .ruff_cache
