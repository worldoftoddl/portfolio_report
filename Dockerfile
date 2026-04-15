# syntax=docker/dockerfile:1.7
# Python 백엔드 (FastAPI). 개발용 이미지 — 볼륨 마운트 + uvicorn --reload 전제.
FROM python:3.12-slim

# pandas/lxml/pykrx 빌드 경로용 시스템 의존성
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# uv 바이너리만 공식 이미지에서 복사 (멀티스테이지 패턴)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# 의존성 캐시 레이어 — pyproject.toml / uv.lock 변경 시에만 재설치
COPY pyproject.toml uv.lock ./
RUN uv sync --extra web --frozen --no-install-project

# 프로젝트 소스
COPY src ./src
COPY README.md ./
RUN uv sync --extra web --frozen

EXPOSE 8000

# compose가 --reload 포함 명령으로 오버라이드. 단독 실행(예: docker run) 기본은 서비스 모드.
CMD ["uv", "run", "portfolio-report", "serve", "--host", "0.0.0.0", "--port", "8000"]
