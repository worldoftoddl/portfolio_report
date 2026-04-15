.PHONY: install test test-cov lint fmt run clean \
        dev dev-local dev-backend dev-frontend stop compose-down

# --- Python 도구 ---

install:
	uv sync --extra web

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

# --- 개발 서버 ---

# Docker Compose로 백엔드 + 프런트 동시 실행 (권장).
# Docker Desktop WSL 통합이 활성화되어 있어야 한다.
dev:
	docker compose up --build

# Docker 없이 로컬 프로세스로 둘 다 실행 (fallback).
# 한 터미널로 두 서버를 묶어 Ctrl-C 한 번으로 모두 종료.
dev-local:
	@echo "[dev-local] 백엔드(8000) + 프런트(3000) 로컬 실행. Ctrl-C로 종료."
	@trap 'kill 0' EXIT INT TERM; \
	  uv run portfolio-report serve --host 127.0.0.1 --port 8000 --reload & \
	  (cd web && npm run dev) & \
	  wait

dev-backend:
	uv run portfolio-report serve --host 127.0.0.1 --port 8000 --reload

dev-frontend:
	cd web && npm run dev

stop compose-down:
	-docker compose down
