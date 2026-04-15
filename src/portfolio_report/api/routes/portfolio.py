"""`POST /api/portfolio` — 포트폴리오 분석 엔드포인트.

`PortfolioAnalyzer`는 동기 + 블로킹 코어이므로 `asyncio.to_thread`로
이벤트 루프 블로킹을 방지한다. 세마포어는 Phase 6d-3에서 추가.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends

from portfolio_report.analysis.aggregator import PortfolioAnalyzer
from portfolio_report.analysis.technical import Indicator
from portfolio_report.api.deps import acquire_naver_semaphore, get_analyzer
from portfolio_report.api.errors import APIError
from portfolio_report.api.schemas import PortfolioAnalyzeRequest
from portfolio_report.models.portfolio import PortfolioReport

router = APIRouter(prefix="/api", tags=["portfolio"])


@router.post(
    "/portfolio",
    response_model=PortfolioReport,
    dependencies=[Depends(acquire_naver_semaphore)],
)
async def analyze_portfolio(
    payload: PortfolioAnalyzeRequest,
    analyzer: PortfolioAnalyzer = Depends(get_analyzer),
) -> PortfolioReport:
    try:
        indicators = payload.validated_indicators()
    except ValueError as e:
        raise APIError(str(e), status_code=400, error_code="invalid_indicator") from e

    typed_indicators: list[Indicator] | None = (
        indicators if indicators else None  # type: ignore[assignment]
    )

    report = await asyncio.to_thread(
        analyzer.analyze,
        payload.holdings,
        typed_indicators,
        payload.ohlcv_days,
        payload.use_llm,
    )
    return report
