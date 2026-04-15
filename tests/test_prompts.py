"""LLM 프롬프트 빌더 단위 테스트.

프롬프트가 할루시네이션을 유도하지 않도록, 수치/종목 식별자/데이터 부재 표기가
명확히 포함되는지 검증.
"""

from __future__ import annotations

import pytest

from portfolio_report.llm.base import TechnicalContext
from portfolio_report.llm.prompts import (
    build_technical_system_prompt,
    build_technical_user_prompt,
)


def make_ctx(signals=None, price_tail=None, price=100.0) -> TechnicalContext:
    return TechnicalContext(
        code="005930",
        name="삼성전자",
        current_price=price,
        signals=signals or {},
        price_tail=price_tail or [],
    )


class TestSystemPrompt:
    def test_mentions_role_and_language(self):
        p = build_technical_system_prompt()
        assert "한국어" in p or "한국" in p
        # 투자 자문이 아님을 명시 (면책)
        assert "자문" in p or "참고" in p

    def test_forbids_hallucination(self):
        p = build_technical_system_prompt()
        # 제공된 수치 이외의 값을 추정하지 말라는 지시
        assert ("제공된" in p and "수치" in p) or ("근거" in p) or ("사실" in p)


class TestUserPrompt:
    def test_includes_code_and_name(self):
        ctx = make_ctx()
        p = build_technical_user_prompt(ctx)
        assert "005930" in p
        assert "삼성전자" in p

    def test_includes_current_price(self):
        ctx = make_ctx(price=67890.0)
        p = build_technical_user_prompt(ctx)
        assert "67,890" in p or "67890" in p

    def test_current_price_none_shows_na(self):
        ctx = make_ctx(price=None)
        p = build_technical_user_prompt(ctx)
        assert "N/A" in p or "미확보" in p or "없음" in p

    def test_includes_each_indicator_name_and_signal(self):
        signals = {
            "ichimoku": {
                "close": 70000,
                "tenkan": 69000,
                "kijun": 68000,
                "span_a": 67000,
                "span_b": 65000,
                "signal": "구름대 위 (강세)",
            },
            "rsi": {"value": 72.5, "signal": "과매수 (72.5)"},
            "macd": {
                "macd": 150.0,
                "signal_line": 120.0,
                "histogram": 30.0,
                "signal": "강세",
            },
            "bb": {
                "upper": 75000,
                "middle": 70000,
                "lower": 65000,
                "percent_b": 0.95,
                "signal": "상단 근접",
            },
        }
        ctx = make_ctx(signals=signals)
        p = build_technical_user_prompt(ctx)
        # 각 지표명이 등장
        for kw in ("일목균형표", "RSI", "MACD", "볼린저"):
            assert kw in p, f"'{kw}' 누락"
        # 주요 수치가 포함
        assert "72.5" in p
        assert "과매수" in p
        assert "구름대 위" in p
        assert "상단 근접" in p

    def test_empty_signals_still_valid(self):
        """지표 없는 경우에도 프롬프트가 생성되어야 함."""
        ctx = make_ctx(signals={})
        p = build_technical_user_prompt(ctx)
        assert "005930" in p
        assert "삼성전자" in p

    def test_price_tail_summary_present_when_supplied(self):
        tail = [
            {"Date": "2026-04-10", "Open": 100, "High": 102, "Low": 99, "Close": 101, "Volume": 1000},
            {"Date": "2026-04-11", "Open": 101, "High": 104, "Low": 101, "Close": 103, "Volume": 1500},
        ]
        ctx = make_ctx(price_tail=tail)
        p = build_technical_user_prompt(ctx)
        # 최근 시세 테이블이나 요약이 포함
        assert "2026-04-11" in p
        assert "103" in p

    def test_prompt_request_includes_disclaimer_hint(self):
        """프롬프트가 모델에게 '참고용' 해석을 요구."""
        ctx = make_ctx()
        p = build_technical_user_prompt(ctx)
        assert "해석" in p or "설명" in p

    def test_numeric_values_rendered_not_as_python_repr(self):
        """1234.5678 같은 값이 python repr 그대로 나오지 않도록 (소수점 통제)."""
        ctx = make_ctx(
            signals={"rsi": {"value": 72.567891234, "signal": "과매수 (72.6)"}}
        )
        p = build_technical_user_prompt(ctx)
        # 장황한 소수점(..891234)이 원본 그대로 들어가지 않음
        assert "72.567891234" not in p


class TestFmtValueBranches:
    def test_int_formatted_with_thousands(self):
        ctx = make_ctx(
            signals={"rsi": {"value": 1_234_567, "signal": "-"}}
        )
        p = build_technical_user_prompt(ctx)
        assert "1,234,567" in p

    def test_small_float_two_decimals(self):
        ctx = make_ctx(
            signals={"rsi": {"value": 45.5, "signal": "-"}}
        )
        p = build_technical_user_prompt(ctx)
        assert "45.50" in p

    def test_non_numeric_value_rendered_as_string(self):
        ctx = make_ctx(
            signals={"rsi": {"value": "some_text", "signal": "-"}}
        )
        p = build_technical_user_prompt(ctx)
        assert "some_text" in p


def test_system_prompt_is_nonempty_string():
    p = build_technical_system_prompt()
    assert isinstance(p, str)
    assert len(p) > 50


def test_user_prompt_is_nonempty_string():
    p = build_technical_user_prompt(make_ctx())
    assert isinstance(p, str)
    assert len(p) > 50
