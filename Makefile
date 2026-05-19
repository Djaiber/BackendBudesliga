.PHONY: install test lint typecheck format check convert-xml run-local-replay clean help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	python -m pip install --upgrade pip
	pip install -e ".[dev]"

test: ## Run all tests
	pytest

test-unit: ## Run unit tests only
	pytest tests/unit/ -m unit

test-integration: ## Run integration tests only
	pytest tests/integration/ -m integration

test-cov: ## Run tests with coverage report
	pytest --cov=src --cov-report=html --cov-report=term

lint: ## Run ruff linter
	ruff check src/ tests/ scripts/

format: ## Format code with ruff
	ruff format src/ tests/ scripts/
	ruff check --fix src/ tests/ scripts/

typecheck: ## Run mypy type checker
	mypy src/ scripts/

check: lint typecheck test ## Run all checks (lint, typecheck, test)

convert-xml: ## Convert XML datasets to JSON
	python scripts/convert_xml_to_json.py

run-local-replay: ## Run replay engine locally (no AWS)
	python scripts/run_local_replay.py --speed 600

upload-replay: ## Upload replay data to S3
	./scripts/upload_to_s3.sh

clean: ## Clean generated files
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

clean-output: ## Clean converted output files
	rm -rf scripts/output/

docker-up: ## Start localstack for local testing
	docker-compose up -d

docker-down: ## Stop localstack
	docker-compose down

docker-logs: ## Show localstack logs
	docker-compose logs -f
