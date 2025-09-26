.PHONY: help build up down restart logs shell test clean docker-dev docker-prod

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
run: ## Run the application (development mode)
	uv run uvicorn src.app:app --reload

build: ## Build Docker images
	docker-compose build

docker-dev: ## Start with default .env file (development)
	docker-compose up --build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## View logs from all services
	docker-compose logs -f

logs-app: ## View logs from app service only
	docker-compose logs -f app

logs-celery: ## View logs from celery worker only
	docker-compose logs -f celery-worker

shell: ## Open shell in app container
	docker-compose exec app /bin/bash

shell-root: ## Open root shell in app container
	docker-compose exec -u root app /bin/bash

test: ## Run tests
	docker-compose exec app uv run pytest

clean: ## Remove containers, volumes, and images
	docker-compose down -v --rmi all

dev: ## Start development environment
	docker-compose up --build

prod: ## Start production environment (detached)
	docker-compose up -d --build

status: ## Show status of all services
	docker-compose ps

redis-cli: ## Open Redis CLI
	docker-compose exec redis redis-cli

psql: ## Open PostgreSQL CLI
	docker-compose exec postgres psql -U agent -d agent_orchestrator

# Database management targets
init-db: ## Initialize database schema
	uv run python scripts/init_db.py init

reset-db: ## Reset database (WARNING: This will delete all data)
	uv run python scripts/init_db.py reset

db-stats: ## Show database statistics
	@uv run python -c "import asyncio; from src.db.config import DatabaseConfig; from src.db.db_connector import AsyncDBConnector; async def stats(): async with AsyncDBConnector(DatabaseConfig.from_env()) as db: print(await db.get_outcome_stats()); asyncio.run(stats())"

flower: ## Open Celery Flower in browser
	@echo "Celery Flower is available at: http://localhost:5555"

api: ## Open API documentation in browser
	@echo "API documentation is available at: http://localhost:8000/docs"