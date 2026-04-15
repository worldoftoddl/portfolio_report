"""포트폴리오 분석 오케스트레이션.

- 입력: HoldingInput 리스트 (종목명/코드 + 수량)
- 과정: 종목 해석 → 네이버 데이터 수집 (병렬) → 가중평균 집계
- 출력: PortfolioReport
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from portfolio_report.analysis.technical import (
    ALL_INDICATORS,
    Indicator,
    compute_indicators,
)
from portfolio_report.analysis.valuation import (
    weighted_beta,
    weighted_forward_per,
    weighted_per,
)
from portfolio_report.config import Settings, get_settings
from portfolio_report.data.naver_client import NaverClient
from portfolio_report.data.price_client import PriceClient
from portfolio_report.data.ticker_resolver import TickerResolver
from portfolio_report.models.holding import Holding, HoldingInput
from portfolio_report.models.portfolio import (
    Portfolio,
    PortfolioAggregates,
    PortfolioReport,
    TechnicalAnalysis,
)
from portfolio_report.models.stock import StockInfo
from portfolio_report.reporting.charts import Overlay, Subplot, compose_chart

logger = logging.getLogger(__name__)


class PortfolioAnalyzer:
    def __init__(
        self,
        settings: Settings | None = None,
        naver_client: NaverClient | None = None,
        price_client: PriceClient | None = None,
        resolver: TickerResolver | None = None,
    ):
        self.settings = settings or get_settings()
        self._naver = naver_client
        self._price = price_client or PriceClient()
        self._resolver = resolver or TickerResolver(self.settings)
        self._warnings: list[str] = []

    def analyze(
        self,
        inputs: list[HoldingInput],
        indicators: list[Indicator] | None = None,
        ohlcv_days: int = 180,
    ) -> PortfolioReport:
        holdings = self._resolve_all(inputs)
        self._fetch_all(holdings)
        aggregates = self._aggregate(holdings)
        analyses: list[TechnicalAnalysis] = []
        if indicators:
            analyses = self._compute_technicals(holdings, indicators, ohlcv_days)
        return PortfolioReport(
            generated_at=datetime.now(),
            portfolio=Portfolio(holdings=holdings),
            aggregates=aggregates,
            per_stock_analyses=analyses,
            warnings=list(self._warnings),
        )

    # --- steps ---

    def _resolve_all(self, inputs: list[HoldingInput]) -> list[Holding]:
        holdings: list[Holding] = []
        for item in inputs:
            resolved = self._resolver.resolve(item)
            for w in resolved.warnings:
                self._warnings.append(w)
                logger.warning(w)
            holdings.append(
                Holding(code=resolved.code, name=resolved.name, quantity=item.quantity)
            )
        return holdings

    def _fetch_all(self, holdings: list[Holding]) -> None:
        """NaverClient로 각 종목 데이터를 병렬 수집. 실패 시 가격만 FDR 폴백."""
        client = self._naver or NaverClient(self.settings)
        owns_client = self._naver is None
        try:
            with ThreadPoolExecutor(
                max_workers=self.settings.naver_concurrent_requests
            ) as pool:
                futures = {
                    pool.submit(self._fetch_single, client, h): h for h in holdings
                }
                for fut in as_completed(futures):
                    holding = futures[fut]
                    try:
                        holding.stock = fut.result()
                    except Exception as e:
                        msg = f"[{holding.code} {holding.name}] 데이터 수집 실패: {e}"
                        logger.warning(msg)
                        self._warnings.append(msg)
                        holding.stock = self._fallback_stock(holding)
        finally:
            if owns_client:
                client.close()

    def _fetch_single(self, client: NaverClient, holding: Holding) -> StockInfo:
        snap = client.fetch_snapshot(holding.code)
        main = client.fetch_main_info(holding.code)
        wise = client.fetch_wisereport(holding.code)
        return StockInfo(
            code=holding.code,
            name=holding.name,
            current_price=snap.get("current_price"),
            market_cap=snap.get("market_cap"),
            per=main.get("per"),
            forward_per=main.get("forward_per"),
            eps=main.get("eps"),
            beta=wise.get("beta"),
        )

    def _fallback_stock(self, holding: Holding) -> StockInfo:
        """네이버 전체 실패 시 최소한 현재가만이라도 FDR로 시도."""
        price = self._price.get_current_price_fallback(holding.code)
        return StockInfo(code=holding.code, name=holding.name, current_price=price)

    def _compute_technicals(
        self,
        holdings: list[Holding],
        names: list[Indicator],
        ohlcv_days: int,
    ) -> list[TechnicalAnalysis]:
        invalid = set(names) - set(ALL_INDICATORS)
        if invalid:
            raise ValueError(f"알 수 없는 지표: {invalid}. 사용 가능: {ALL_INDICATORS}")

        overlays: list[Overlay] = [n for n in names if n in ("ichimoku", "bb")]  # type: ignore[misc]
        subplots: list[Subplot] = [n for n in names if n in ("rsi", "macd")]  # type: ignore[misc]

        analyses: list[TechnicalAnalysis] = []
        for h in holdings:
            try:
                ohlcv = self._price.get_ohlcv(h.code, days=ohlcv_days)
            except Exception as e:
                msg = f"[{h.code} {h.name}] OHLCV 수집 실패: {e}"
                logger.warning(msg)
                self._warnings.append(msg)
                continue
            result = compute_indicators(ohlcv, names)
            fig = compose_chart(
                result.df.tail(min(120, len(result.df))),
                overlays=overlays,
                subplots=subplots,
                title=f"{h.code} {h.name}",
            )
            analyses.append(
                TechnicalAnalysis(
                    code=h.code,
                    name=h.name,
                    indicators=result.signals,
                    chart_html=fig.to_html(include_plotlyjs="cdn", full_html=False),
                )
            )
        return analyses

    def _aggregate(self, holdings: list[Holding]) -> PortfolioAggregates:
        per, per_cov = weighted_per(holdings)
        fwd, fwd_cov = weighted_forward_per(holdings)
        beta, beta_cov = weighted_beta(holdings)
        return PortfolioAggregates(
            weighted_per=per,
            weighted_forward_per=fwd,
            weighted_beta=beta,
            per_coverage=per_cov,
            forward_per_coverage=fwd_cov,
            beta_coverage=beta_cov,
            total_market_value=sum(h.market_value or 0.0 for h in holdings),
        )
