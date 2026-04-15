"""네이버 실패 시 펀더멘털(PER/EPS/베타) 폴백 클라이언트.

- PER/PBR/EPS: pykrx (`get_market_fundamental`)
- 52주 베타: KS11(KOSPI) 대비 252거래일 일간수익률 회귀
- 코스닥 종목은 벤치마크 불일치 한계를 warning으로 기록

수치 계산(`compute_beta_from_returns`)은 순수 함수로 단위 테스트 커버.
외부 IO(`_get_close_series`, `_get_market_fundamental`)는 모킹 대상으로 분리.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd

logger = logging.getLogger(__name__)

MIN_SAMPLES = 30  # 베타 계산 최소 샘플 수


@dataclass
class BetaResult:
    """베타 계산 결과. 벤치마크/기간 메타 보존."""

    value: float | None
    benchmark: str = "KS11"
    lookback_days: int = 252
    warnings: list[str] = field(default_factory=list)


def compute_beta_from_returns(
    stock_returns: list[float] | pd.Series,
    market_returns: list[float] | pd.Series,
) -> float | None:
    """β = Cov(R_stock, R_market) / Var(R_market).

    - 두 시리즈 길이 불일치 / 30개 미만 / 시장 분산 0 → None
    - NaN은 dropna 후 계산
    """
    s = pd.Series(stock_returns, dtype="float64").reset_index(drop=True)
    m = pd.Series(market_returns, dtype="float64").reset_index(drop=True)
    if s.empty or m.empty or len(s) != len(m):
        return None
    # Pair drop NaN
    pair = pd.concat([s, m], axis=1, keys=["s", "m"]).dropna()
    if len(pair) < MIN_SAMPLES:
        return None
    market_var = pair["m"].var(ddof=1)
    if market_var == 0 or pd.isna(market_var):
        return None
    cov = pair["s"].cov(pair["m"])
    if pd.isna(cov):
        return None
    return float(cov / market_var)


# --- External IO (모킹 지점) ---

def _get_close_series(code: str, start: date, end: date) -> pd.Series:
    """FinanceDataReader 래핑. 종목코드('005930') 또는 지수심볼('KS11') 모두 지원."""
    import FinanceDataReader as fdr

    df = fdr.DataReader(code, start, end)
    return df["Close"]


def _get_market_fundamental(code: str, date_str: str | None = None) -> pd.DataFrame:
    """pykrx 래핑. 단일 종목의 최근 펀더멘털."""
    from pykrx import stock

    if date_str is None:
        date_str = _recent_business_day().strftime("%Y%m%d")
    # 특정 일자 단일 종목
    df = stock.get_market_fundamental(date_str, date_str, code)
    return df


def _recent_business_day() -> date:
    today = date.today()
    # 주말 회피 (간단 근사, 공휴일은 무시)
    wd = today.weekday()
    if wd == 5:
        return today - timedelta(days=1)
    if wd == 6:
        return today - timedelta(days=2)
    return today


class FundamentalFallbackClient:
    """pykrx/FDR 기반 폴백."""

    def get_fundamental(self, code: str, date_str: str | None = None) -> dict:
        try:
            df = _get_market_fundamental(code, date_str)
        except Exception as e:
            logger.warning("[%s] pykrx 펀더멘털 조회 실패: %s", code, e)
            return {"per": None, "pbr": None, "eps": None}
        if df is None or df.empty:
            return {"per": None, "pbr": None, "eps": None}
        row = df.iloc[-1]
        return {
            "per": _safe_float(row.get("PER")),
            "pbr": _safe_float(row.get("PBR")),
            "eps": _safe_float(row.get("EPS")),
        }

    def compute_beta(
        self,
        code: str,
        benchmark: str = "KS11",
        lookback_days: int = 252,
        market: str | None = None,
    ) -> BetaResult:
        warnings: list[str] = []
        if market and market.upper() == "KOSDAQ":
            warnings.append(
                f"[{code}] 코스닥 종목을 KOSPI({benchmark}) 벤치마크로 회귀 — "
                "벤치마크 불일치 한계 있음. 해석 시 주의."
            )

        end = _recent_business_day()
        # 주말/공휴일 보정 + 252 영업일 확보 위해 여유 추가
        start = end - timedelta(days=int(lookback_days * 1.6) + 30)

        try:
            stock_close = _get_close_series(code, start, end)
            market_close = _get_close_series(benchmark, start, end)
        except Exception as e:
            warnings.append(f"[{code}] 베타 폴백 실패 (가격 수집 오류): {e}")
            return BetaResult(
                value=None, benchmark=benchmark, lookback_days=lookback_days, warnings=warnings
            )

        stock_returns = stock_close.pct_change().dropna().tail(lookback_days)
        market_returns = market_close.pct_change().dropna().tail(lookback_days)

        # 공통 인덱스 교집합
        common = stock_returns.index.intersection(market_returns.index)
        if len(common) < MIN_SAMPLES:
            warnings.append(
                f"[{code}] 베타 계산 샘플 부족 ({len(common)}일 < {MIN_SAMPLES}일)"
            )
            return BetaResult(
                value=None, benchmark=benchmark, lookback_days=lookback_days, warnings=warnings
            )

        beta = compute_beta_from_returns(
            stock_returns.loc[common], market_returns.loc[common]
        )
        return BetaResult(
            value=beta, benchmark=benchmark, lookback_days=lookback_days, warnings=warnings
        )


def _safe_float(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
