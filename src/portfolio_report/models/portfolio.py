from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from portfolio_report.models.holding import Holding


class Coverage(BaseModel):
    """가중평균에 포함된 종목 비율 정보."""

    metric: str
    included_value: float = 0.0
    excluded_value: float = 0.0
    excluded_codes: list[str] = Field(default_factory=list)

    @property
    def total_value(self) -> float:
        return self.included_value + self.excluded_value

    @property
    def ratio(self) -> float:
        total = self.total_value
        return self.included_value / total if total > 0 else 0.0


class PortfolioAggregates(BaseModel):
    """포트폴리오 집계 지표."""

    weighted_per: float | None = None
    weighted_forward_per: float | None = None
    weighted_beta: float | None = None

    per_coverage: Coverage
    forward_per_coverage: Coverage
    beta_coverage: Coverage

    total_market_value: float = 0.0


class Portfolio(BaseModel):
    holdings: list[Holding]

    @property
    def total_market_value(self) -> float:
        return sum(h.market_value or 0.0 for h in self.holdings)

    def weight_of(self, holding: Holding) -> float:
        total = self.total_market_value
        if total <= 0 or holding.market_value is None:
            return 0.0
        return holding.market_value / total


class TechnicalAnalysis(BaseModel):
    """종목별 기술적 분석 결과."""

    code: str
    name: str
    indicators: dict[str, dict] = Field(default_factory=dict)
    chart_html: str | None = None
    llm_explanation: str | None = None


class PortfolioReport(BaseModel):
    """최종 리포트 객체. 출력 계층에서 변환."""

    generated_at: datetime
    portfolio: Portfolio
    aggregates: PortfolioAggregates
    per_stock_analyses: list[TechnicalAnalysis] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
