"""기술적 지표 계산 (pandas-ta 래퍼).

지원 지표:
- ichimoku: 전환선(ITS_9), 기준선(IKS_26), 선행스팬A(ISA_9), 선행스팬B(ISB_26), 후행스팬(ICS_26)
- rsi: 기본 14일
- macd: 기본 12/26/9
- bollinger: 기본 20일 ±2σ
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import pandas as pd
import pandas_ta as ta

Indicator = Literal["ichimoku", "rsi", "macd", "bb"]
ALL_INDICATORS: tuple[Indicator, ...] = ("ichimoku", "rsi", "macd", "bb")


@dataclass
class TechnicalIndicators:
    """지표 계산 결과. 원본 OHLCV와 동일한 인덱스의 데이터프레임 + 신호 요약."""

    df: pd.DataFrame  # 원본 + 지표 컬럼 추가
    signals: dict[str, dict] = field(default_factory=dict)


def compute_ichimoku(df: pd.DataFrame) -> pd.DataFrame:
    """일목균형표 컬럼을 추가한 DataFrame 반환.

    추가 컬럼: ITS_9 (전환선), IKS_26 (기준선),
               ISA_9 (선행스팬A), ISB_26 (선행스팬B), ICS_26 (후행스팬)
    """
    visible, _ = ta.ichimoku(df["High"], df["Low"], df["Close"])
    return df.join(visible)


def compute_rsi(df: pd.DataFrame, length: int = 14) -> pd.DataFrame:
    series = ta.rsi(df["Close"], length=length)
    return df.assign(**{f"RSI_{length}": series})


def compute_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    macd = ta.macd(df["Close"], fast=fast, slow=slow, signal=signal)
    return df.join(macd)


def compute_bollinger(df: pd.DataFrame, length: int = 20, std: float = 2.0) -> pd.DataFrame:
    bb = ta.bbands(df["Close"], length=length, std=std)
    return df.join(bb)


def compute_indicators(df: pd.DataFrame, names: list[Indicator]) -> TechnicalIndicators:
    """여러 지표를 순차 적용한 결과."""
    result = df.copy()
    if "ichimoku" in names:
        result = compute_ichimoku(result)
    if "rsi" in names:
        result = compute_rsi(result)
    if "macd" in names:
        result = compute_macd(result)
    if "bb" in names:
        result = compute_bollinger(result)
    return TechnicalIndicators(df=result, signals=_summarize(result, names))


def _summarize(df: pd.DataFrame, names: list[Indicator]) -> dict[str, dict]:
    """마지막 행 기준 지표값 + 신호 해석 문자열 생성. LLM 프롬프트 재료."""
    out: dict[str, dict] = {}
    if df.empty:
        return out
    last = df.iloc[-1]
    close = float(last["Close"])

    if "ichimoku" in names and "ITS_9" in df.columns:
        tenkan = _safe(last.get("ITS_9"))
        kijun = _safe(last.get("IKS_26"))
        span_a = _safe(last.get("ISA_9"))
        span_b = _safe(last.get("ISB_26"))
        out["ichimoku"] = {
            "close": close,
            "tenkan": tenkan,
            "kijun": kijun,
            "span_a": span_a,
            "span_b": span_b,
            "signal": _ichimoku_signal(close, tenkan, kijun, span_a, span_b),
        }

    if "rsi" in names and "RSI_14" in df.columns:
        rsi = _safe(last.get("RSI_14"))
        out["rsi"] = {
            "value": rsi,
            "signal": _rsi_signal(rsi),
        }

    if "macd" in names and "MACD_12_26_9" in df.columns:
        macd = _safe(last.get("MACD_12_26_9"))
        signal = _safe(last.get("MACDs_12_26_9"))
        hist = _safe(last.get("MACDh_12_26_9"))
        prev_hist = _safe(df["MACDh_12_26_9"].iloc[-2]) if len(df) >= 2 else None
        out["macd"] = {
            "macd": macd,
            "signal_line": signal,
            "histogram": hist,
            "signal": _macd_signal(hist, prev_hist),
        }

    if "bb" in names and "BBU_20_2.0_2.0" in df.columns:
        upper = _safe(last.get("BBU_20_2.0_2.0"))
        middle = _safe(last.get("BBM_20_2.0_2.0"))
        lower = _safe(last.get("BBL_20_2.0_2.0"))
        pct = _safe(last.get("BBP_20_2.0_2.0"))
        out["bb"] = {
            "upper": upper,
            "middle": middle,
            "lower": lower,
            "percent_b": pct,
            "signal": _bb_signal(pct),
        }

    return out


def _safe(value) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(f):
        return None
    return f


def _ichimoku_signal(
    close: float,
    tenkan: float | None,
    kijun: float | None,
    span_a: float | None,
    span_b: float | None,
) -> str:
    if None in (tenkan, kijun, span_a, span_b):
        return "데이터 부족"
    cloud_top = max(span_a, span_b)
    cloud_bot = min(span_a, span_b)
    if close > cloud_top:
        position = "구름대 위 (강세)"
    elif close < cloud_bot:
        position = "구름대 아래 (약세)"
    else:
        position = "구름대 내부 (중립)"
    cross = "전환선>기준선 (단기 강세)" if tenkan > kijun else "전환선<기준선 (단기 약세)"
    return f"{position}, {cross}"


def _rsi_signal(rsi: float | None) -> str:
    if rsi is None:
        return "데이터 부족"
    if rsi >= 70:
        return f"과매수 ({rsi:.1f})"
    if rsi <= 30:
        return f"과매도 ({rsi:.1f})"
    return f"중립 ({rsi:.1f})"


def _macd_signal(hist: float | None, prev_hist: float | None) -> str:
    if hist is None:
        return "데이터 부족"
    if prev_hist is not None:
        if prev_hist <= 0 < hist:
            return "골든크로스 (매수 신호)"
        if prev_hist >= 0 > hist:
            return "데드크로스 (매도 신호)"
    return "강세" if hist > 0 else "약세"


def _bb_signal(pct_b: float | None) -> str:
    if pct_b is None:
        return "데이터 부족"
    if pct_b >= 1.0:
        return "상단 돌파 (과열)"
    if pct_b <= 0.0:
        return "하단 이탈 (침체)"
    if pct_b >= 0.8:
        return "상단 근접"
    if pct_b <= 0.2:
        return "하단 근접"
    return "밴드 내부 (중립)"
