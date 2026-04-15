"""FastAPI 의존성 주입 헬퍼.

`app.state`에 저장된 싱글톤 인스턴스를 요청 단위로 꺼내 쓴다.
테스트에서는 `app.dependency_overrides[get_analyzer] = lambda: mock`로 교체.

## 세마포어 설계 (6d-3)

`acquire_naver_semaphore`는 네이버/FDR 외부 호출에 의존하는 경로에만 적용한다.
즉 `POST /api/portfolio`와 `GET /api/stock/{code}/ohlcv`에만 `Depends`로 엮고,
Claude API만 호출하는 `POST /api/stock/{code}/llm-explain`에는 엮지 않는다.
LLM 요청이 외부 업스트림 스로틀로 불필요하게 블로킹되는 것을 방지.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request

from portfolio_report.analysis.aggregator import PortfolioAnalyzer
from portfolio_report.data.price_client import PriceClient
from portfolio_report.data.ticker_resolver import TickerResolver
from portfolio_report.llm.base import BaseLLMClient


def get_analyzer(request: Request) -> PortfolioAnalyzer:
    return request.app.state.analyzer


def get_price_client(request: Request) -> PriceClient:
    return request.app.state.price_client


def get_resolver(request: Request) -> TickerResolver:
    return request.app.state.resolver


def get_llm_client(request: Request) -> BaseLLMClient | None:
    return getattr(request.app.state, "llm_client", None)


async def acquire_naver_semaphore(request: Request) -> AsyncIterator[None]:
    """네이버 호출 경로 전용 세마포어 획득 의존성.

    FastAPI는 `yield` 의존성을 async context처럼 다룬다 — 핸들러 완료 후
    자동으로 release된다.
    """
    sem = request.app.state.naver_semaphore
    async with sem:
        yield
