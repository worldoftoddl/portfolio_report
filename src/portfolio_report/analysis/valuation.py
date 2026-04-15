"""포트폴리오 가중평균 및 커버리지 계산.

정책:
- 지표 값이 None인 종목은 가중평균에서 제외하고 Coverage에 기록.
- 평가금액(market_value)이 None인 종목도 제외 (가격 미확보).
- 포함 종목이 하나도 없으면 가중평균은 None.
- 음수 값(적자 PER 등)은 수학적으로 유효하므로 포함. 경고는 호출자가 판단.
"""

from __future__ import annotations

from typing import Callable

from portfolio_report.models.holding import Holding
from portfolio_report.models.portfolio import Coverage
from portfolio_report.models.stock import StockInfo

ValueGetter = Callable[[StockInfo], float | None]


def weighted_average(
    holdings: list[Holding],
    value_of: ValueGetter,
    metric_name: str,
) -> tuple[float | None, Coverage]:
    coverage = Coverage(metric=metric_name)
    numerator = 0.0

    for h in holdings:
        market_value = h.market_value
        value = value_of(h.stock) if h.stock is not None else None

        if market_value is None or value is None:
            if market_value is not None:
                coverage.excluded_value += market_value
            coverage.excluded_codes.append(h.code)
            continue

        numerator += value * market_value
        coverage.included_value += market_value

    if coverage.included_value == 0:
        return None, coverage
    return numerator / coverage.included_value, coverage


def weighted_per(holdings: list[Holding]) -> tuple[float | None, Coverage]:
    return weighted_average(holdings, lambda s: s.per, "per")


def weighted_forward_per(holdings: list[Holding]) -> tuple[float | None, Coverage]:
    return weighted_average(holdings, lambda s: s.forward_per, "forward_per")


def weighted_beta(holdings: list[Holding]) -> tuple[float | None, Coverage]:
    return weighted_average(holdings, lambda s: s.beta, "beta")
