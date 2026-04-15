"""FastAPI 앱 팩토리 + lifespan.

## 핵심 설계 (사용자 피드백 반영)

`lifespan` 컨텍스트 매니저에서 앱 시작 시 `NaverClient`/`PortfolioAnalyzer` 등을
**한 번만** 생성하여 `app.state`에 저장한다. 이로써:

- `httpx.Client` 커넥션 풀이 요청 간 재사용 → 프론트 연속 호출 성능 확보
- 개별 라우트는 `Depends(get_analyzer)`로 그 싱글톤을 받아 사용
- 앱 종료 시 `naver_client.close()`로 리소스 정리

테스트 경로는 `create_app(analyzer=mock_analyzer, ...)`로 lifespan을 우회하고
`app.state`에 직접 주입하거나 `app.dependency_overrides`로 교체한다.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from portfolio_report.analysis.aggregator import PortfolioAnalyzer
from portfolio_report.api.errors import register_exception_handlers
from portfolio_report.config import Settings, get_settings
from portfolio_report.data.fundamental_fallback import FundamentalFallbackClient
from portfolio_report.data.naver_client import NaverClient
from portfolio_report.data.price_client import PriceClient
from portfolio_report.data.ticker_resolver import TickerResolver
from portfolio_report.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


def _build_default_analyzer(
    settings: Settings,
) -> tuple[PortfolioAnalyzer, NaverClient, PriceClient, TickerResolver]:
    naver = NaverClient(settings)
    price = PriceClient()
    resolver = TickerResolver(settings)
    fundamental = FundamentalFallbackClient()
    analyzer = PortfolioAnalyzer(
        settings=settings,
        naver_client=naver,
        price_client=price,
        resolver=resolver,
        fundamental_fallback=fundamental,
    )
    return analyzer, naver, price, resolver


@asynccontextmanager
async def _default_lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    analyzer, naver, price, resolver = _build_default_analyzer(settings)
    app.state.analyzer = analyzer
    app.state.naver_client = naver
    app.state.price_client = price
    app.state.resolver = resolver
    logger.info("API 앱 시작: analyzer/naver/price/resolver 초기화 완료")
    try:
        yield
    finally:
        try:
            naver.close()
        except Exception:  # pragma: no cover - 정리 실패는 무시
            logger.warning("NaverClient close 실패", exc_info=True)


def create_app(
    *,
    analyzer: PortfolioAnalyzer | None = None,
    price_client: PriceClient | None = None,
    resolver: TickerResolver | None = None,
    llm_client: BaseLLMClient | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    """앱 팩토리.

    - 프로덕션: 인자 없이 호출 → `lifespan`이 실제 클라이언트 생성
    - 테스트: `analyzer` 등을 주입 → lifespan 스킵, 주입된 mock 사용
    """
    resolved_settings = settings or get_settings()

    if analyzer is not None:
        # 테스트 경로: lifespan 없이 state에 직접 주입
        app = FastAPI(title="portfolio-report API")
        app.state.analyzer = analyzer
        app.state.price_client = price_client or analyzer._price  # type: ignore[attr-defined]
        app.state.resolver = resolver or analyzer._resolver  # type: ignore[attr-defined]
        if llm_client is not None:
            app.state.llm_client = llm_client
    else:
        app = FastAPI(title="portfolio-report API", lifespan=_default_lifespan)

    app.state.settings = resolved_settings
    # 네이버/FDR 호출 경로 동시성 제한용 싱글톤 세마포어 (LLM 경로는 미적용)
    app.state.naver_semaphore = asyncio.Semaphore(resolved_settings.api_concurrency_limit)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    # 라우터 등록 (지연 import로 circular 회피)
    from portfolio_report.api.routes.portfolio import router as portfolio_router
    from portfolio_report.api.routes.technical import router as technical_router

    app.include_router(portfolio_router)
    app.include_router(technical_router)

    return app
