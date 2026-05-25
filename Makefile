.PHONY: help install up down migrate dev dev-frontend \
        run-ingest run-process run-analysis run-research \
        test lint lint-fix load-test clean

help:
	@echo "MarketPulse — development commands"
	@echo ""
	@echo "  make install        Install Python + Node dependencies"
	@echo "  make up             Start Kafka, Redis, PostgreSQL"
	@echo "  make down           Stop all Docker services"
	@echo "  make migrate        Run Alembic migrations"
	@echo "  make dev            Start API with hot-reload on :8000"
	@echo "  make dev-frontend   Start Next.js dev server on :3000"
	@echo "  make run-ingest     Start ingestion service"
	@echo "  make run-process    Start processing (LLM enrichment) service"
	@echo "  make run-analysis   Start market analysis service"
	@echo "  make run-research   Start stock universe refresh service"
	@echo "  make test           Run pytest suite"
	@echo "  make lint           Ruff + ESLint check"
	@echo "  make lint-fix       Auto-fix lint issues"
	@echo "  make load-test      Locust load test (requires running API)"
	@echo "  make clean          Remove caches"

install:
	pip install -r backend/requirements.txt
	cd frontend && npm install

up:
	docker compose up -d postgres redis kafka
	@echo "Waiting for services…"
	@sleep 5

down:
	docker compose down

migrate:
	cd backend && alembic upgrade head

dev:
	cd backend && uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

dev-frontend:
	cd frontend && npm run dev

run-ingest:
	cd backend && python -m src.ingestion.runner

run-process:
	cd backend && python -m src.processing.consumer

run-analysis:
	cd backend && python -m src.analysis.consumer

run-research:
	cd backend && python -m src.research.runner

test:
	cd backend && pytest --tb=short

lint:
	cd backend && ruff check src/ tests/
	cd frontend && npm run lint

lint-fix:
	cd backend && ruff check --fix src/ tests/
	cd frontend && npm run lint -- --fix

load-test:
	locust -f backend/tests/locustfile.py --host http://localhost:8000 \
	       --users 20 --spawn-rate 5 --run-time 2m --headless

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	rm -rf backend/.pytest_cache backend/.ruff_cache
	rm -rf frontend/.next frontend/node_modules/.cache
