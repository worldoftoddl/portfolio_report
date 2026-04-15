"""가중평균 + 커버리지 계산 단위 테스트.

수치 정확성이 포트폴리오 분석의 critical path이므로 100% 커버리지 목표.
"""

from __future__ import annotations

import math

import pytest

from portfolio_report.analysis.valuation import (
    weighted_average,
    weighted_beta,
    weighted_forward_per,
    weighted_per,
)
from portfolio_report.models.holding import Holding
from portfolio_report.models.stock import StockInfo


def make_holding(
    code: str = "A",
    quantity: float = 1,
    price: float | None = 100,
    per: float | None = None,
    forward_per: float | None = None,
    beta: float | None = None,
) -> Holding:
    stock = StockInfo(
        code=code,
        name=f"name-{code}",
        current_price=price,
        per=per,
        forward_per=forward_per,
        beta=beta,
    )
    return Holding(code=code, name=stock.name, quantity=quantity, stock=stock)


class TestWeightedAverageGeneric:
    def test_equal_weights(self):
        """동일 평가금액 2종목의 PER 평균은 산술평균."""
        holdings = [
            make_holding("A", quantity=1, price=100, per=10),
            make_holding("B", quantity=1, price=100, per=20),
        ]
        avg, cov = weighted_average(holdings, lambda s: s.per, "per")
        assert avg == pytest.approx(15.0)
        assert cov.included_value == 200
        assert cov.excluded_value == 0
        assert cov.ratio == 1.0

    def test_unequal_weights(self):
        """평가금액 3:1 비율로 가중평균 계산."""
        holdings = [
            make_holding("A", quantity=3, price=100, per=10),   # mv=300
            make_holding("B", quantity=1, price=100, per=30),   # mv=100
        ]
        avg, cov = weighted_average(holdings, lambda s: s.per, "per")
        # (10 * 300 + 30 * 100) / 400 = 6000 / 400 = 15
        assert avg == pytest.approx(15.0)
        assert cov.included_value == 400

    def test_missing_value_excluded(self):
        """PER None인 종목은 제외되고 커버리지에 기록."""
        holdings = [
            make_holding("A", quantity=1, price=100, per=10),   # 포함
            make_holding("B", quantity=2, price=100, per=None), # 제외
        ]
        avg, cov = weighted_average(holdings, lambda s: s.per, "per")
        assert avg == pytest.approx(10.0)
        assert cov.included_value == 100
        assert cov.excluded_value == 200
        assert cov.excluded_codes == ["B"]
        assert cov.ratio == pytest.approx(100 / 300)

    def test_missing_price_excluded(self):
        """가격 미확보(market_value=None) 종목은 제외."""
        holdings = [
            make_holding("A", quantity=1, price=100, per=10),
            make_holding("B", quantity=2, price=None, per=20),
        ]
        avg, cov = weighted_average(holdings, lambda s: s.per, "per")
        assert avg == pytest.approx(10.0)
        assert "B" in cov.excluded_codes

    def test_all_missing_returns_none(self):
        holdings = [
            make_holding("A", quantity=1, price=100, per=None),
            make_holding("B", quantity=1, price=100, per=None),
        ]
        avg, cov = weighted_average(holdings, lambda s: s.per, "per")
        assert avg is None
        assert cov.included_value == 0
        assert cov.excluded_value == 200
        assert set(cov.excluded_codes) == {"A", "B"}
        assert cov.ratio == 0.0

    def test_empty_holdings(self):
        avg, cov = weighted_average([], lambda s: s.per, "per")
        assert avg is None
        assert cov.included_value == 0
        assert cov.excluded_value == 0
        assert cov.ratio == 0.0

    def test_single_holding(self):
        holdings = [make_holding("A", quantity=5, price=200, per=12.5)]
        avg, cov = weighted_average(holdings, lambda s: s.per, "per")
        assert avg == pytest.approx(12.5)
        assert cov.ratio == 1.0

    def test_negative_per_included(self):
        """적자 기업(PER 음수)은 포함되어야 함. 제외 정책은 호출자 몫."""
        holdings = [
            make_holding("A", quantity=1, price=100, per=20),
            make_holding("B", quantity=1, price=100, per=-10),
        ]
        avg, cov = weighted_average(holdings, lambda s: s.per, "per")
        assert avg == pytest.approx(5.0)
        assert cov.included_value == 200

    def test_holding_without_stockinfo_excluded(self):
        """Holding.stock이 None이면 제외."""
        h = Holding(code="X", name="X", quantity=1, stock=None)
        avg, cov = weighted_average([h], lambda s: s.per, "per")
        assert avg is None
        assert "X" in cov.excluded_codes

    def test_metric_name_passed_through(self):
        holdings = [make_holding("A", quantity=1, price=100, per=10)]
        _, cov = weighted_average(holdings, lambda s: s.per, "per")
        assert cov.metric == "per"


class TestWeightedPer:
    def test_returns_tuple_and_metric_name(self):
        holdings = [
            make_holding("A", quantity=1, price=100, per=10, forward_per=8, beta=1.0),
            make_holding("B", quantity=1, price=100, per=20, forward_per=None, beta=None),
        ]
        avg, cov = weighted_per(holdings)
        assert avg == pytest.approx(15.0)
        assert cov.metric == "per"
        assert cov.ratio == 1.0


class TestWeightedForwardPer:
    def test_excludes_missing_forward(self):
        holdings = [
            make_holding("A", quantity=1, price=100, per=10, forward_per=8),    # 포함
            make_holding("B", quantity=3, price=100, per=20, forward_per=None), # 제외
        ]
        avg, cov = weighted_forward_per(holdings)
        assert avg == pytest.approx(8.0)
        assert cov.metric == "forward_per"
        assert cov.excluded_codes == ["B"]
        assert cov.ratio == pytest.approx(100 / 400)


class TestWeightedBeta:
    def test_weighted_beta_basic(self):
        holdings = [
            make_holding("A", quantity=1, price=100, beta=1.0),
            make_holding("B", quantity=1, price=300, beta=2.0),
        ]
        avg, cov = weighted_beta(holdings)
        # (1.0 * 100 + 2.0 * 300) / 400 = 700/400 = 1.75
        assert avg == pytest.approx(1.75)
        assert cov.metric == "beta"

    def test_beta_missing_excluded(self):
        holdings = [
            make_holding("A", quantity=1, price=100, beta=1.2),
            make_holding("B", quantity=1, price=100, beta=None),
        ]
        avg, cov = weighted_beta(holdings)
        assert avg == pytest.approx(1.2)
        assert "B" in cov.excluded_codes


def test_coverage_conservation():
    """included_value + excluded_value == total_market_value (가격 있는 종목만)."""
    holdings = [
        make_holding("A", quantity=1, price=100, per=10),
        make_holding("B", quantity=2, price=100, per=None),   # per 없음
        make_holding("C", quantity=1, price=None, per=15),    # 가격 없음
    ]
    _, cov = weighted_per(holdings)
    # 가격이 있는 종목의 총합 = 100 + 200 = 300
    assert cov.included_value + cov.excluded_value == 300


def test_no_nan_outputs():
    holdings = [make_holding("A", quantity=1, price=100, per=15.5)]
    avg, _ = weighted_per(holdings)
    assert avg is not None
    assert not math.isnan(avg)
