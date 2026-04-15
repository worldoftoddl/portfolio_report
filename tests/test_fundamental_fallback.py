"""펀더멘털 폴백 단위 테스트.

베타 계산은 수치 정확성이 중요하므로 고정 시계열로 기대값 검증.
pykrx/FDR 호출은 모킹.
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from portfolio_report.data.fundamental_fallback import (
    BetaResult,
    FundamentalFallbackClient,
    compute_beta_from_returns,
)


class TestComputeBetaFromReturns:
    def test_perfect_correlation_beta_1(self):
        """stock 수익률 = market 수익률이면 베타 = 1.0."""
        market = [0.01, -0.02, 0.03, 0.00, -0.01] * 10  # 50개
        stock = list(market)
        beta = compute_beta_from_returns(stock, market)
        assert beta == pytest.approx(1.0, abs=1e-9)

    def test_double_market_beta_2(self):
        """stock = 2 * market이면 베타 = 2.0."""
        market = [0.01, -0.02, 0.03, 0.00, -0.01] * 10
        stock = [r * 2 for r in market]
        beta = compute_beta_from_returns(stock, market)
        assert beta == pytest.approx(2.0, abs=1e-9)

    def test_inverse_correlation_beta_negative(self):
        """stock = -market이면 베타 = -1.0."""
        market = [0.01, -0.02, 0.03, 0.00, -0.01] * 10
        stock = [-r for r in market]
        beta = compute_beta_from_returns(stock, market)
        assert beta == pytest.approx(-1.0, abs=1e-9)

    def test_zero_correlation_returns_value_near_zero(self):
        """시장 변동과 무관한 상수 수익률은 베타 ≈ 0."""
        market = [0.01, -0.02, 0.03, -0.01, 0.02] * 10
        stock = [0.005] * 50  # 상수 → 공분산 0
        beta = compute_beta_from_returns(stock, market)
        assert beta == pytest.approx(0.0, abs=1e-9)

    def test_too_few_samples_returns_none(self):
        """30개 미만이면 None."""
        assert compute_beta_from_returns([0.01] * 20, [0.01] * 20) is None

    def test_length_mismatch_returns_none(self):
        assert compute_beta_from_returns([0.01] * 50, [0.01] * 40) is None

    def test_zero_market_variance_returns_none(self):
        """시장이 전혀 움직이지 않으면 Var=0이라 베타 정의 불가."""
        market = [0.0] * 50
        stock = [0.01, -0.01] * 25
        assert compute_beta_from_returns(stock, market) is None

    def test_empty_returns_none(self):
        assert compute_beta_from_returns([], []) is None


class TestBetaResultModel:
    def test_default_benchmark_and_lookback(self):
        r = BetaResult(value=1.2)
        assert r.benchmark == "KS11"
        assert r.lookback_days == 252
        assert r.warnings == []

    def test_none_value_allowed(self):
        r = BetaResult(value=None)
        assert r.value is None


class TestFundamentalFallbackClient:
    def _price_df(self, prices: list[float]) -> pd.DataFrame:
        """Close 컬럼만 있는 DataFrame."""
        idx = pd.date_range("2025-01-02", periods=len(prices), freq="B")
        return pd.DataFrame({"Close": prices}, index=idx)

    def test_compute_beta_kospi_stock_happy_path(self):
        """FDR을 모킹하여 KOSPI 종목 베타 계산."""
        client = FundamentalFallbackClient()
        # 50일 동일 수익률 → 베타 1.0
        prices = [100 * (1.001 ** i) for i in range(55)]

        with patch(
            "portfolio_report.data.fundamental_fallback._get_close_series"
        ) as mock_fetch:
            mock_fetch.side_effect = [
                self._price_df(prices)["Close"],
                self._price_df(prices)["Close"],
            ]
            result = client.compute_beta("005930", benchmark="KS11", lookback_days=54)

        assert isinstance(result, BetaResult)
        assert result.value == pytest.approx(1.0, abs=1e-6)
        assert result.benchmark == "KS11"
        assert result.warnings == []

    def test_compute_beta_kosdaq_adds_warning(self):
        """코스닥 종목은 KS11 대비 베타지만 벤치마크 불일치 warning."""
        client = FundamentalFallbackClient()
        prices = [100 * (1.001 ** i) for i in range(55)]

        with patch(
            "portfolio_report.data.fundamental_fallback._get_close_series"
        ) as mock_fetch:
            mock_fetch.side_effect = [
                self._price_df(prices)["Close"],
                self._price_df(prices)["Close"],
            ]
            result = client.compute_beta(
                "035760", benchmark="KS11", lookback_days=54, market="KOSDAQ"
            )

        assert result.value is not None
        assert any("KOSDAQ" in w or "코스닥" in w for w in result.warnings), (
            "코스닥 종목은 벤치마크 불일치 경고 필요"
        )

    def test_compute_beta_returns_none_on_fetch_failure(self):
        client = FundamentalFallbackClient()
        with patch(
            "portfolio_report.data.fundamental_fallback._get_close_series"
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("network down")
            result = client.compute_beta("005930")
        assert result.value is None
        assert any("폴백" in w or "실패" in w for w in result.warnings)

    def test_get_fundamental_happy_path(self):
        client = FundamentalFallbackClient()
        fake = pd.DataFrame(
            {"PER": [32.34], "PBR": [3.32], "EPS": [6564.0], "DIV": [0.79]},
            index=[pd.Timestamp("2026-04-14")],
        )
        with patch("portfolio_report.data.fundamental_fallback._get_market_fundamental") as mock_f:
            mock_f.return_value = fake
            result = client.get_fundamental("005930")
        assert result["per"] == pytest.approx(32.34)
        assert result["pbr"] == pytest.approx(3.32)
        assert result["eps"] == pytest.approx(6564.0)

    def test_get_fundamental_returns_none_on_empty(self):
        client = FundamentalFallbackClient()
        with patch("portfolio_report.data.fundamental_fallback._get_market_fundamental") as mock_f:
            mock_f.return_value = pd.DataFrame()
            result = client.get_fundamental("005930")
        assert result["per"] is None
        assert result["eps"] is None


class TestSampleShortage:
    def _short_df(self, n: int) -> pd.Series:
        idx = pd.date_range("2026-04-01", periods=n, freq="B")
        return pd.Series([100 + i for i in range(n)], index=idx, name="Close")

    def test_common_samples_below_min(self):
        """공통 인덱스가 30개 미만이면 None + warning."""
        client = FundamentalFallbackClient()
        with patch(
            "portfolio_report.data.fundamental_fallback._get_close_series"
        ) as mock_fetch:
            mock_fetch.side_effect = [self._short_df(20), self._short_df(20)]
            result = client.compute_beta("005930", lookback_days=20)
        assert result.value is None
        assert any("샘플" in w for w in result.warnings)


def test_no_nan_in_valid_beta_computation():
    market = [0.01, -0.02, 0.03, 0.00, -0.01] * 10
    stock = [r * 1.3 for r in market]
    beta = compute_beta_from_returns(stock, market)
    assert beta is not None
    assert not math.isnan(beta)
    assert beta == pytest.approx(1.3, abs=1e-9)
