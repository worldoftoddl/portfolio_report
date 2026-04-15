"""Lightweight Charts 시리얼라이저 순수 함수 테스트.

계약:
- time은 "YYYY-MM-DD" 문자열
- 각 라인 시리즈는 `[{time, value}, ...]`
- NaN 값은 해당 포인트 제외 (Lightweight Charts는 gap 허용)
- 요청된 지표만 출력 (도메인 모델 오염 방지)
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from portfolio_report.api.serializers import to_tradingview_series


@pytest.fixture
def ohlcv_df() -> pd.DataFrame:
    """5영업일 OHLCV + 일부 지표 컬럼 포함 DataFrame."""
    idx = pd.date_range("2026-01-05", periods=5, freq="B")
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0, 103.0, 104.0],
            "High": [105.0, 106.0, 107.0, 108.0, 109.0],
            "Low": [99.0, 100.0, 101.0, 102.0, 103.0],
            "Close": [104.0, 105.0, 106.0, 107.0, 108.0],
            "Volume": [1000, 1100, 1200, 1300, 1400],
        },
        index=idx,
    )


class TestOhlcvBasics:
    def test_ohlcv_emits_yyyy_mm_dd_time(self, ohlcv_df):
        out = to_tradingview_series(ohlcv_df, indicators=[])
        assert "ohlcv" in out
        assert len(out["ohlcv"]) == 5
        first = out["ohlcv"][0]
        assert first["time"] == "2026-01-05"
        assert first["open"] == 100.0
        assert first["high"] == 105.0
        assert first["low"] == 99.0
        assert first["close"] == 104.0
        assert first["volume"] == 1000

    def test_empty_df_returns_empty_series(self):
        empty = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        out = to_tradingview_series(empty, indicators=[])
        assert out["ohlcv"] == []
        assert out["indicators"] == {}

    def test_unknown_indicator_is_ignored(self, ohlcv_df):
        out = to_tradingview_series(ohlcv_df, indicators=["unknown"])  # type: ignore[list-item]
        assert out["indicators"] == {}


class TestRSI:
    def test_rsi_emits_points_with_nan_dropped(self, ohlcv_df):
        df = ohlcv_df.assign(RSI_14=[float("nan"), float("nan"), 45.0, 52.0, 60.0])
        out = to_tradingview_series(df, indicators=["rsi"])
        rsi = out["indicators"]["rsi"]
        assert rsi == [
            {"time": "2026-01-07", "value": 45.0},
            {"time": "2026-01-08", "value": 52.0},
            {"time": "2026-01-09", "value": 60.0},
        ]

    def test_rsi_missing_column_emits_empty(self, ohlcv_df):
        out = to_tradingview_series(ohlcv_df, indicators=["rsi"])
        assert out["indicators"]["rsi"] == []


class TestMACD:
    def test_macd_emits_three_series(self, ohlcv_df):
        df = ohlcv_df.assign(
            MACD_12_26_9=[float("nan"), 0.1, 0.2, 0.3, 0.4],
            MACDs_12_26_9=[float("nan"), 0.05, 0.15, 0.25, 0.35],
            MACDh_12_26_9=[float("nan"), 0.05, 0.05, 0.05, 0.05],
        )
        out = to_tradingview_series(df, indicators=["macd"])
        macd = out["indicators"]["macd"]
        assert set(macd.keys()) == {"macd", "signal", "hist"}
        assert len(macd["macd"]) == 4  # NaN 1개 드롭
        assert macd["signal"][0] == {"time": "2026-01-06", "value": 0.05}
        assert macd["hist"][-1] == {"time": "2026-01-09", "value": 0.05}


class TestBollinger:
    def test_bb_emits_upper_mid_lower(self, ohlcv_df):
        df = ohlcv_df.assign(
            **{
                "BBU_20_2.0_2.0": [110.0, 111.0, 112.0, 113.0, 114.0],
                "BBM_20_2.0_2.0": [104.0, 105.0, 106.0, 107.0, 108.0],
                "BBL_20_2.0_2.0": [98.0, 99.0, 100.0, 101.0, 102.0],
            }
        )
        out = to_tradingview_series(df, indicators=["bb"])
        bb = out["indicators"]["bb"]
        assert set(bb.keys()) == {"upper", "mid", "lower"}
        assert bb["upper"][0] == {"time": "2026-01-05", "value": 110.0}
        assert bb["mid"][2] == {"time": "2026-01-07", "value": 106.0}
        assert bb["lower"][-1] == {"time": "2026-01-09", "value": 102.0}


class TestIchimoku:
    def test_ichimoku_emits_four_spans(self, ohlcv_df):
        df = ohlcv_df.assign(
            ITS_9=[100.0, 101.0, 102.0, 103.0, 104.0],
            IKS_26=[99.0, 100.0, 101.0, 102.0, 103.0],
            ISA_9=[98.0, 99.0, 100.0, 101.0, 102.0],
            ISB_26=[97.0, 98.0, 99.0, 100.0, 101.0],
        )
        out = to_tradingview_series(df, indicators=["ichimoku"])
        ich = out["indicators"]["ichimoku"]
        assert set(ich.keys()) == {"tenkan", "kijun", "span_a", "span_b"}
        assert ich["tenkan"][0] == {"time": "2026-01-05", "value": 100.0}
        assert ich["span_b"][-1] == {"time": "2026-01-09", "value": 101.0}


class TestMultipleIndicators:
    def test_combined_indicators(self, ohlcv_df):
        df = ohlcv_df.assign(
            RSI_14=[30.0, 40.0, 50.0, 60.0, 70.0],
            **{
                "BBU_20_2.0_2.0": [110.0, 111.0, 112.0, 113.0, 114.0],
                "BBM_20_2.0_2.0": [104.0, 105.0, 106.0, 107.0, 108.0],
                "BBL_20_2.0_2.0": [98.0, 99.0, 100.0, 101.0, 102.0],
            },
        )
        out = to_tradingview_series(df, indicators=["rsi", "bb"])
        assert "rsi" in out["indicators"]
        assert "bb" in out["indicators"]
        assert "macd" not in out["indicators"]
        assert "ichimoku" not in out["indicators"]


def test_nan_in_ohlcv_is_dropped():
    """OHLCV 자체에 NaN이 있는 행(휴장일 보간 등)은 해당 행 전체 제외."""
    idx = pd.date_range("2026-01-05", periods=3, freq="B")
    df = pd.DataFrame(
        {
            "Open": [100.0, math.nan, 102.0],
            "High": [105.0, math.nan, 107.0],
            "Low": [99.0, math.nan, 101.0],
            "Close": [104.0, math.nan, 106.0],
            "Volume": [1000, 1100, 1200],
        },
        index=idx,
    )
    out = to_tradingview_series(df, indicators=[])
    assert len(out["ohlcv"]) == 2
    assert [p["time"] for p in out["ohlcv"]] == ["2026-01-05", "2026-01-07"]
