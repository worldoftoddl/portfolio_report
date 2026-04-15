"""FinanceDataReader 기반 가격/펀더멘털 폴백 클라이언트.

네이버가 불가할 때 또는 기술적 분석용 과거 OHLCV를 가져올 때 사용.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import pandas as pd

from portfolio_report.data.cache import cached, price_ttl

logger = logging.getLogger(__name__)


class PriceClient:
    """가격 이력 및 펀더멘털 폴백 조회."""

    def get_ohlcv(self, code: str, days: int = 180) -> pd.DataFrame:
        """최근 N일 OHLCV 반환. 기술적 지표 계산용.

        반환 컬럼: Open, High, Low, Close, Volume (인덱스는 날짜).
        """
        return _get_ohlcv_cached(code, days)

    def get_current_price_fallback(self, code: str) -> float | None:
        try:
            df = self.get_ohlcv(code, days=5)
            if df.empty:
                return None
            return float(df["Close"].iloc[-1])
        except Exception as e:
            logger.warning("가격 폴백 실패 %s: %s", code, e)
            return None


@cached("price", price_ttl)
def _get_ohlcv_cached(code: str, days: int) -> pd.DataFrame:
    import FinanceDataReader as fdr

    end = date.today()
    start = end - timedelta(days=days + 30)  # 주말/휴일 고려 여유
    df = fdr.DataReader(code, start, end)
    # FDR은 통상 Open/High/Low/Close/Volume/Change 컬럼 반환
    expected = {"Open", "High", "Low", "Close", "Volume"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"FDR 응답에서 누락된 컬럼: {missing}")
    return df[list(expected - {"Volume"}) + ["Volume"]].tail(days)
