.PHONY: lint format typecheck test check ci clean install

# Run linter (same as CI)
lint:
	uv run ruff check src tests

# Check formatting (same as CI)
format:
	uv run ruff format --check src tests

# Run type checker (optional, CI uses continue-on-error)
typecheck:
	uv run mypy src || true

# Run tests
test:
	uv run pytest tests/ -v --tb=short

# Run all checks that CI enforces (lint + format + test)
check: lint format test

# Run full CI simulation including typecheck
ci: lint format typecheck test

# Quick test (no verbose)
test-quick:
	uv run pytest tests/ -q

# Auto-fix lint issues
fix:
	uv run ruff check --fix src tests
	uv run ruff format src tests

# Install dependencies
install:
	uv sync --dev

# Clean cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
