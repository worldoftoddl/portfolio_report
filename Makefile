.PHONY: install test lint run clean

install:
	uv sync

test:
	uv run pytest

test-cov:
	uv run pytest --cov=src/portfolio_report --cov-report=term-missing

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

fmt:
	uv run ruff format src tests
	uv run ruff check --fix src tests

run:
	uv run portfolio-report analyze -i examples/portfolio.yaml

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov dist build
	find . -type d -name __pycache__ -exec rm -rf {} +
