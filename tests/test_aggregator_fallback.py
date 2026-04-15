"""aggregator._fallback_stock 폴백 경로 통합 테스트.

NaverClient 전체 실패 + FundamentalFallbackClient 모킹으로 PER/베타 복구 검증.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from portfolio_report.analysis.aggregator import PortfolioAnalyzer
from portfolio_report.data.fundamental_fallback import BetaResult
from portfolio_report.models.holding import HoldingInput


def make_fake_naver_all_fail() -> MagicMock:
    client = MagicMock()
    client.fetch_snapshot.side_effect = RuntimeError("naver down")
    client.fetch_main_info.side_effect = RuntimeError("naver down")
    client.fetch_wisereport.side_effect = RuntimeError("naver down")
    client.close.return_value = None
    return client


def make_fake_price_client(price: float = 70000) -> MagicMock:
    pc = MagicMock()
    pc.get_current_price_fallback.return_value = price
    return pc


def make_fake_fundamental(per: float, eps: float, beta: float) -> MagicMock:
    ff = MagicMock()
    ff.get_fundamental.return_value = {"per": per, "pbr": 2.5, "eps": eps}
    ff.compute_beta.return_value = BetaResult(value=beta, benchmark="KS11", lookback_days=252)
    return ff


def make_fake_resolver(code: str = "005930", name: str = "삼성전자", market: str = "KOSPI"):
    resolver = MagicMock()
    resolved = MagicMock()
    resolved.code = code
    resolved.name = name
    resolved.warnings = []
    resolver.resolve.return_value = resolved
    resolver.master = pd.DataFrame(
        [{"code": code, "name": name, "market": market}]
    )
    return resolver


class TestFallbackRecovery:
    def test_naver_all_fail_per_and_beta_recovered(self):
        """네이버 전 엔드포인트 실패 시에도 PER/EPS/베타가 폴백으로 채워짐."""
        analyzer = PortfolioAnalyzer(
            naver_client=make_fake_naver_all_fail(),
            price_client=make_fake_price_client(price=70000),
            resolver=make_fake_resolver("005930", "삼성전자", "KOSPI"),
            fundamental_fallback=make_fake_fundamental(per=15.0, eps=5000.0, beta=1.1),
        )
        report = analyzer.analyze([HoldingInput(code="005930", quantity=10)])

        holding = report.portfolio.holdings[0]
        stock = holding.stock
        assert stock is not None
        assert stock.current_price == pytest.approx(70000)
        assert stock.per == pytest.approx(15.0)
        assert stock.eps == pytest.approx(5000.0)
        assert stock.beta == pytest.approx(1.1)

        assert any("펀더멘털 폴백" in w for w in report.warnings)

    def test_kosdaq_stock_adds_benchmark_warning(self):
        """코스닥 종목은 벤치마크 불일치 warning이 리포트에 포함."""
        ff = MagicMock()
        ff.get_fundamental.return_value = {"per": 20.0, "eps": 1000, "pbr": 3.0}
        ff.compute_beta.return_value = BetaResult(
            value=1.3,
            benchmark="KS11",
            warnings=["[035760] 코스닥 종목을 KOSPI 벤치마크로 회귀 — 해석 주의"],
        )
        analyzer = PortfolioAnalyzer(
            naver_client=make_fake_naver_all_fail(),
            price_client=make_fake_price_client(price=50000),
            resolver=make_fake_resolver("035760", "CJ ENM", "KOSDAQ"),
            fundamental_fallback=ff,
        )
        report = analyzer.analyze([HoldingInput(code="035760", quantity=5)])
        assert any("코스닥" in w for w in report.warnings)

    def test_partial_fallback_beta_none_does_not_break(self):
        """베타 실패(샘플 부족 등)해도 PER/가격은 남아있어야 함."""
        ff = MagicMock()
        ff.get_fundamental.return_value = {"per": 12.5, "eps": 3000, "pbr": 1.2}
        ff.compute_beta.return_value = BetaResult(
            value=None, warnings=["[005930] 베타 계산 샘플 부족"]
        )
        analyzer = PortfolioAnalyzer(
            naver_client=make_fake_naver_all_fail(),
            price_client=make_fake_price_client(price=70000),
            resolver=make_fake_resolver("005930", "삼성전자", "KOSPI"),
            fundamental_fallback=ff,
        )
        report = analyzer.analyze([HoldingInput(code="005930", quantity=10)])
        stock = report.portfolio.holdings[0].stock
        assert stock.per == pytest.approx(12.5)
        assert stock.beta is None
