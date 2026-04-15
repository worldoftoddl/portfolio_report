"""LLM 캐시 키 생성 단위 테스트.

실제 Claude API 호출은 모킹으로 검증 (ClaudeClient 쪽은 별도 테스트).
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from portfolio_report.llm.base import TechnicalContext
from portfolio_report.llm.cache import llm_cache_key, signals_hash

KST = ZoneInfo("Asia/Seoul")


def make_ctx(
    code: str = "005930",
    name: str = "삼성전자",
    price: float | None = 70000,
    signals: dict | None = None,
    price_tail: list | None = None,
) -> TechnicalContext:
    return TechnicalContext(
        code=code,
        name=name,
        current_price=price,
        signals=signals if signals is not None else {"rsi": {"value": 60, "signal": "중립"}},
        price_tail=price_tail or [],
    )


class TestSignalsHash:
    def test_same_dict_same_hash(self):
        a = {"rsi": {"value": 60, "signal": "중립"}}
        b = {"rsi": {"value": 60, "signal": "중립"}}
        assert signals_hash(a) == signals_hash(b)

    def test_key_order_insensitive(self):
        """키 순서가 달라도 내용이 같으면 같은 해시."""
        a = {"rsi": {"value": 60, "signal": "중립"}, "macd": {"signal": "강세"}}
        b = {"macd": {"signal": "강세"}, "rsi": {"signal": "중립", "value": 60}}
        assert signals_hash(a) == signals_hash(b)

    def test_different_values_different_hash(self):
        a = {"rsi": {"value": 60}}
        b = {"rsi": {"value": 70}}
        assert signals_hash(a) != signals_hash(b)

    def test_empty_dict_has_valid_hash(self):
        h = signals_hash({})
        assert isinstance(h, str)
        assert len(h) > 0

    def test_returns_short_hex_string(self):
        """키 문자열이 과하게 길지 않고 hex 문자만 포함."""
        h = signals_hash({"rsi": {"value": 60}})
        assert len(h) <= 16
        assert all(c in "0123456789abcdef" for c in h)


class TestLLMCacheKey:
    def test_contains_model_code_date_and_hash(self):
        ctx = make_ctx(code="005930")
        now = datetime(2026, 4, 15, 14, 0, tzinfo=KST)
        key = llm_cache_key(ctx, model="claude-sonnet-4-20250514", now=now)
        assert "llm:" in key
        assert "claude-sonnet-4-20250514" in key
        assert "005930" in key
        assert "2026-04-15" in key

    def test_same_input_same_key(self):
        ctx = make_ctx()
        now = datetime(2026, 4, 15, 14, 0, tzinfo=KST)
        k1 = llm_cache_key(ctx, "m", now=now)
        k2 = llm_cache_key(ctx, "m", now=now)
        assert k1 == k2

    def test_different_date_different_key(self):
        ctx = make_ctx()
        k1 = llm_cache_key(ctx, "m", now=datetime(2026, 4, 15, 14, 0, tzinfo=KST))
        k2 = llm_cache_key(ctx, "m", now=datetime(2026, 4, 16, 14, 0, tzinfo=KST))
        assert k1 != k2

    def test_different_signals_different_key(self):
        ctx_a = make_ctx(signals={"rsi": {"value": 60}})
        ctx_b = make_ctx(signals={"rsi": {"value": 70}})
        now = datetime(2026, 4, 15, 14, 0, tzinfo=KST)
        assert llm_cache_key(ctx_a, "m", now=now) != llm_cache_key(ctx_b, "m", now=now)

    def test_different_model_different_key(self):
        ctx = make_ctx()
        now = datetime(2026, 4, 15, 14, 0, tzinfo=KST)
        assert llm_cache_key(ctx, "sonnet", now=now) != llm_cache_key(ctx, "opus", now=now)

    def test_different_code_different_key(self):
        now = datetime(2026, 4, 15, 14, 0, tzinfo=KST)
        k1 = llm_cache_key(make_ctx(code="005930"), "m", now=now)
        k2 = llm_cache_key(make_ctx(code="000660"), "m", now=now)
        assert k1 != k2

    def test_timezone_handled_as_kst(self):
        """KST 기준 하루가 바뀌기 직전/직후는 다른 키 (UTC로 계산하면 충돌)."""
        # KST 2026-04-16 00:30 (= UTC 2026-04-15 15:30)
        late_night = datetime(2026, 4, 16, 0, 30, tzinfo=KST)
        # KST 2026-04-15 23:30
        evening = datetime(2026, 4, 15, 23, 30, tzinfo=KST)
        ctx = make_ctx()
        assert llm_cache_key(ctx, "m", now=late_night) != llm_cache_key(ctx, "m", now=evening)

    def test_price_tail_does_not_affect_key(self):
        """price_tail은 시세 참고용, 키 결정 요인에서 제외 (signals만 의미)."""
        now = datetime(2026, 4, 15, 14, 0, tzinfo=KST)
        ctx_a = make_ctx(price_tail=[{"Date": "2026-04-14", "Close": 70000}])
        ctx_b = make_ctx(price_tail=[{"Date": "2026-04-14", "Close": 71000}])
        assert llm_cache_key(ctx_a, "m", now=now) == llm_cache_key(ctx_b, "m", now=now)


def test_naive_datetime_treated_as_kst():
    """tzinfo 없는 datetime도 KST로 해석."""
    naive = datetime(2026, 4, 15, 14, 0)
    ctx = make_ctx()
    key = llm_cache_key(ctx, "m", now=naive)
    assert "2026-04-15" in key


def test_now_defaults_to_current_kst():
    """now 인자를 생략하면 현재 KST 날짜 사용."""
    ctx = make_ctx()
    key = llm_cache_key(ctx, "m")
    assert isinstance(key, str)
    assert "005930" in key
