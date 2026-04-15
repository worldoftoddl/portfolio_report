"""API 요청/응답 스키마.

- 응답은 기존 도메인 모델(`PortfolioReport` 등)을 그대로 재사용 (오염 방지)
- 요청은 API 경계에서만 의미있는 파라미터를 묶어 별도 정의
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from portfolio_report.analysis.technical import ALL_INDICATORS
from portfolio_report.models.holding import HoldingInput


class PortfolioAnalyzeRequest(BaseModel):
    """`POST /api/portfolio` 요청 본문."""

    holdings: list[HoldingInput] = Field(..., min_length=1)
    indicators: list[str] = Field(default_factory=list)
    ohlcv_days: int = Field(default=180, gt=0, le=1000)
    use_llm: bool = True

    def validated_indicators(self) -> list[str]:
        invalid = set(self.indicators) - set(ALL_INDICATORS)
        if invalid:
            raise ValueError(
                f"알 수 없는 지표: {sorted(invalid)}. 사용 가능: {list(ALL_INDICATORS)}"
            )
        return list(self.indicators)


class OHLCVQueryParams(BaseModel):
    days: int = Field(default=180, gt=0, le=1000)


class LLMExplainRequest(BaseModel):
    """`POST /api/stock/{code}/llm-explain` 요청 본문.

    signals / price_tail은 프론트가 `POST /api/portfolio` 응답에서 받은 것을
    그대로 echo 하도록 설계. 서버에 상태를 남기지 않기 위함.
    """

    name: str
    current_price: float | None = None
    signals: dict = Field(default_factory=dict)
    price_tail: list[dict] = Field(default_factory=list)


class LLMExplainResponse(BaseModel):
    code: str
    explanation: str


class TechnicalSeriesResponse(BaseModel):
    """`GET /api/stock/{code}/ohlcv` 응답."""

    code: str
    name: str
    series: dict  # to_tradingview_series 출력
    # 지표가 요청된 경우 마지막 행 기반 신호 요약(technical._summarize 출력).
    # LLM 해석 요청 시 컨텍스트로 재사용할 수 있도록 함께 노출.
    signals: dict = Field(default_factory=dict)
