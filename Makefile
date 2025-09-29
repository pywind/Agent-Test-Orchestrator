.PHONY: help build up down restart logs shell test clean docker-dev docker-prod \
          migrate migrate-dry migrate-status migrate-validate db-reset db-backup db-restore

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ========================================
# Application Commands
# ========================================

run: ## Run the application (development mode)
	uv run uvicorn src.api.app:app --reload

build: ## Build Docker images
	docker-compose build

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

# ========================================
# Database Migration Commands
# ========================================

migrate: ## Run all pending database migrations
	uv run python scripts/migrate.py --verbose

migrate-dry: ## Show pending migrations without applying them
	uv run python scripts/migrate.py --dry-run

migrate-status: ## Show current migration status
	uv run python scripts/migrate.py --status

migrate-validate: ## Validate migration file integrity
	uv run python scripts/migrate.py --validate

migrate-to: ## Migrate to a specific version (usage: make migrate-to VERSION=5)
	python scripts/migrate.py --target=$(VERSION) --verbose

migrate-docker: ## Run migrations in Docker environment
	docker-compose up migrations

migrate-docker-dry: ## Show pending migrations in Docker environment (dry run)
	docker-compose run --rm migrations python scripts/migrate.py --dry-run

# ========================================
# Database Management Commands
# ========================================

db-reset: ## Reset database (WARNING: destroys all data)
	@echo "⚠️  WARNING: This will destroy all data in the database!"
	@read -p "Are you sure? Type 'yes' to continue: " confirm && [ "$$confirm" = "yes" ]
	docker-compose down postgres
	docker volume rm agent-test-orchestrator_postgres_data || true
	docker-compose up -d postgres
	@echo "Waiting for PostgreSQL to be ready..."
	sleep 10
	make migrate

db-backup: ## Create a database backup
	@if [ -z "$(BACKUP_NAME)" ]; then \
		BACKUP_NAME="backup-$$(date +%Y%m%d-%H%M%S)"; \
	else \
		BACKUP_NAME="$(BACKUP_NAME)"; \
	fi; \
	docker-compose exec postgres pg_dump -U $${POSTGRES_USER:-agent} $${POSTGRES_DB:-agent_orchestrator} > "backups/$$BACKUP_NAME.sql" && \
	echo "✅ Database backup created: backups/$$BACKUP_NAME.sql"

db-restore: ## Restore database from backup (usage: make db-restore BACKUP_FILE=backup.sql)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "❌ Please specify BACKUP_FILE (usage: make db-restore BACKUP_FILE=backup.sql)"; \
		exit 1; \
	fi
	@if [ ! -f "$(BACKUP_FILE)" ]; then \
		echo "❌ Backup file $(BACKUP_FILE) not found"; \
		exit 1; \
	fi
	@echo "⚠️  WARNING: This will overwrite the current database!"
	@read -p "Are you sure? Type 'yes' to continue: " confirm && [ "$$confirm" = "yes" ]
	docker-compose exec -T postgres psql -U $${POSTGRES_USER:-agent} $${POSTGRES_DB:-agent_orchestrator} < "$(BACKUP_FILE)"
	@echo "✅ Database restored from $(BACKUP_FILE)"

db-shell: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U $${POSTGRES_USER:-agent} $${POSTGRES_DB:-agent_orchestrator}

# ========================================
# Development & Testing Commands
# ========================================

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