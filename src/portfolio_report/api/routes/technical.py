"""`/api/stock/{code}/*` — 종목별 차트/LLM 해석 엔드포인트.

- `GET  /api/stock/{code}/ohlcv` : 지표 시계열(Lightweight Charts 포맷)
- `POST /api/stock/{code}/llm-explain` : 비스트리밍 LLM 해석 (스트리밍은 6f)
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Query

from portfolio_report.analysis.technical import ALL_INDICATORS, Indicator, compute_indicators
from portfolio_report.api.deps import (
    acquire_naver_semaphore,
    get_llm_client,
    get_price_client,
    get_resolver,
)
from portfolio_report.api.errors import APIError
from portfolio_report.api.schemas import (
    LLMExplainRequest,
    LLMExplainResponse,
    TechnicalSeriesResponse,
)
from portfolio_report.api.serializers import to_tradingview_series
from portfolio_report.data.price_client import PriceClient
from portfolio_report.data.ticker_resolver import TickerResolver
from portfolio_report.llm.base import BaseLLMClient, TechnicalContext
from portfolio_report.models.holding import HoldingInput

router = APIRouter(prefix="/api/stock", tags=["technical"])


@router.get(
    "/{code}/ohlcv",
    response_model=TechnicalSeriesResponse,
    dependencies=[Depends(acquire_naver_semaphore)],
)
async def get_ohlcv(
    code: str,
    days: int = Query(default=180, gt=0, le=1000),
    indicators: list[str] = Query(default_factory=list),
    price_client: PriceClient = Depends(get_price_client),
    resolver: TickerResolver = Depends(get_resolver),
) -> TechnicalSeriesResponse:
    invalid = set(indicators) - set(ALL_INDICATORS)
    if invalid:
        raise APIError(
            f"알 수 없는 지표: {sorted(invalid)}",
            status_code=400,
            error_code="invalid_indicator",
        )

    resolved = resolver.resolve(HoldingInput(code=code, quantity=1))

    try:
        df = await asyncio.to_thread(price_client.get_ohlcv, resolved.code, days)
    except Exception as e:
        raise APIError(
            f"OHLCV 수집 실패: {e}",
            status_code=503,
            error_code="upstream_unavailable",
        ) from e

    typed_indicators: list[Indicator] = list(indicators)  # type: ignore[assignment]
    if typed_indicators:
        result = compute_indicators(df, typed_indicators)
        df = result.df

    series = to_tradingview_series(df, typed_indicators)
    return TechnicalSeriesResponse(code=resolved.code, name=resolved.name, series=series)


@router.post("/{code}/llm-explain", response_model=LLMExplainResponse)
async def llm_explain(
    code: str,
    payload: LLMExplainRequest,
    llm: BaseLLMClient | None = Depends(get_llm_client),
) -> LLMExplainResponse:
    if llm is None:
        raise APIError(
            "LLM 클라이언트가 구성되지 않았습니다 (ANTHROPIC_API_KEY 미설정)",
            status_code=503,
            error_code="llm_unavailable",
        )

    ctx = TechnicalContext(
        code=code,
        name=payload.name,
        current_price=payload.current_price,
        signals=payload.signals,
        price_tail=payload.price_tail,
    )
    try:
        explanation = await asyncio.to_thread(llm.explain_technical, ctx)
    except Exception as e:
        raise APIError(str(e), status_code=502, error_code="llm_failure") from e

    return LLMExplainResponse(code=code, explanation=explanation)
