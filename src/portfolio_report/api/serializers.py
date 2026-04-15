"""도메인 DataFrame → Lightweight Charts JSON 포맷 변환.

도메인 모델(`TechnicalAnalysis` 등)을 수정하지 않고 API 계층에서 직렬화.

포맷 계약:
- time: "YYYY-MM-DD" 문자열 (Lightweight Charts business-day 포맷)
- 라인 시리즈: [{"time", "value"}, ...], NaN 지점은 제외
- OHLCV: [{"time","open","high","low","close","volume"}, ...], NaN 행 전체 제외
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from portfolio_report.analysis.technical import Indicator

_OHLCV_COLS = ("Open", "High", "Low", "Close")


def to_tradingview_series(
    df: pd.DataFrame,
    indicators: list[Indicator] | list[str],
) -> dict[str, Any]:
    """OHLCV + 요청된 지표만 Lightweight Charts 포맷으로 변환.

    df는 `analysis.technical.compute_indicators(...).df`를 그대로 넘기면 된다.
    요청되지 않은 지표는 출력되지 않는다 (도메인 모델 오염 방지).
    """
    return {
        "ohlcv": _ohlcv_points(df),
        "indicators": _indicator_series(df, indicators),
    }


def _ohlcv_points(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    cols = [c for c in _OHLCV_COLS if c in df.columns]
    if not cols:
        return []
    valid = df.dropna(subset=cols)
    points: list[dict[str, Any]] = []
    for idx, row in valid.iterrows():
        points.append(
            {
                "time": _format_time(idx),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": _safe_int(row.get("Volume")),
            }
        )
    return points


def _indicator_series(
    df: pd.DataFrame,
    indicators: list[Indicator] | list[str],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name in indicators:
        if name == "rsi":
            out["rsi"] = _line(df, "RSI_14")
        elif name == "macd":
            out["macd"] = {
                "macd": _line(df, "MACD_12_26_9"),
                "signal": _line(df, "MACDs_12_26_9"),
                "hist": _line(df, "MACDh_12_26_9"),
            }
        elif name == "bb":
            out["bb"] = {
                "upper": _line(df, "BBU_20_2.0_2.0"),
                "mid": _line(df, "BBM_20_2.0_2.0"),
                "lower": _line(df, "BBL_20_2.0_2.0"),
            }
        elif name == "ichimoku":
            out["ichimoku"] = {
                "tenkan": _line(df, "ITS_9"),
                "kijun": _line(df, "IKS_26"),
                "span_a": _line(df, "ISA_9"),
                "span_b": _line(df, "ISB_26"),
            }
    return out


def _line(df: pd.DataFrame, column: str) -> list[dict[str, Any]]:
    if column not in df.columns:
        return []
    series = df[column].dropna()
    return [{"time": _format_time(idx), "value": float(v)} for idx, v in series.items()]


def _format_time(idx: Any) -> str:
    if isinstance(idx, pd.Timestamp):
        return idx.strftime("%Y-%m-%d")
    return str(idx)


def _safe_int(value: Any) -> int:
    if value is None or pd.isna(value):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
