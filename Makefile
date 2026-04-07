.PHONY: test lint format check install hooks docs clean help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

test: ## Run tests
	uv run pytest

test-v: ## Run tests (verbose)
	uv run pytest -v

cov: ## Run tests with coverage report
	uv run pytest --cov=data_project_manager --cov-report=term-missing

lint: ## Run ruff linter
	uv run ruff check .

format: ## Auto-format with ruff
	uv run ruff format .

check: ## Lint + format check + tests (CI-like)
	uv run ruff check .
	uv run ruff format --check .
	uv run pytest

install: ## Install in development mode (with enhanced CLI)
	uv sync --extra enhanced

hooks: ## Install pre-commit hooks
	uv run pre-commit install
	uv run pre-commit install --hook-type pre-push

docs: ## Build Sphinx documentation
	uv run sphinx-build -b html docs docs/_build/html

clean: ## Remove build artifacts and caches
	rm -rf __pycache__ .pytest_cache .ruff_cache htmlcov .coverage
	rm -rf dist build *.egg-info src/*.egg-info
	rm -rf docs/_build
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
