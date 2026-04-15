"""ClaudeClient 캐시 동작 통합 테스트.

Anthropic SDK를 모킹하여 동일 입력 시 API 호출 횟수를 검증.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from portfolio_report.config import Settings
from portfolio_report.data.cache import get_cache
from portfolio_report.llm.base import TechnicalContext
from portfolio_report.llm.cache import llm_cache_key


def make_ctx(code: str = "005930", rsi_value: float = 60.0) -> TechnicalContext:
    return TechnicalContext(
        code=code,
        name="삼성전자",
        current_price=70000,
        signals={"rsi": {"value": rsi_value, "signal": "중립"}},
        price_tail=[],
    )


def make_client_with_mock_sdk(monkeypatch, use_cache: bool = True, text: str = "해석 결과"):
    """ClaudeClient + Anthropic SDK 모킹."""
    from portfolio_report.llm import claude_client as cc_module

    settings = Settings(anthropic_api_key="sk-ant-test-key", claude_model="test-model")  # type: ignore[arg-type]

    mock_messages = MagicMock()
    mock_messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)]
    )
    mock_anthropic = MagicMock(return_value=SimpleNamespace(messages=mock_messages))
    monkeypatch.setattr(cc_module, "Anthropic", mock_anthropic)

    client = cc_module.ClaudeClient(settings=settings, use_cache=use_cache)
    return client, mock_messages


@pytest.fixture(autouse=True)
def clear_llm_cache():
    """테스트 격리를 위해 실행 전후 캐시 비움 (llm: prefix만)."""
    cache = get_cache()
    for key in list(cache):
        if isinstance(key, str) and key.startswith("llm:"):
            cache.delete(key)
    yield
    for key in list(cache):
        if isinstance(key, str) and key.startswith("llm:"):
            cache.delete(key)


class TestClaudeCache:
    def test_same_ctx_called_once(self, monkeypatch):
        client, mock_msg = make_client_with_mock_sdk(monkeypatch)
        ctx = make_ctx()

        r1 = client.explain_technical(ctx)
        r2 = client.explain_technical(ctx)
        r3 = client.explain_technical(ctx)

        assert r1 == r2 == r3 == "해석 결과"
        assert mock_msg.create.call_count == 1, "동일 ctx는 SDK 1회만 호출되어야 함"

    def test_different_signals_calls_twice(self, monkeypatch):
        client, mock_msg = make_client_with_mock_sdk(monkeypatch)
        client.explain_technical(make_ctx(rsi_value=60))
        client.explain_technical(make_ctx(rsi_value=70))
        assert mock_msg.create.call_count == 2

    def test_cache_disabled_always_calls(self, monkeypatch):
        client, mock_msg = make_client_with_mock_sdk(monkeypatch, use_cache=False)
        ctx = make_ctx()
        client.explain_technical(ctx)
        client.explain_technical(ctx)
        assert mock_msg.create.call_count == 2

    def test_failure_not_cached(self, monkeypatch):
        """LLM 실패 응답은 캐시하지 않음 → 다음 호출에서 재시도."""
        from portfolio_report.llm import claude_client as cc_module

        settings = Settings(anthropic_api_key="sk-ant-test-key", claude_model="test-model")  # type: ignore[arg-type]

        # 1회차: 실패, 2회차: 성공
        mock_messages = MagicMock()
        success_resp = SimpleNamespace(content=[SimpleNamespace(type="text", text="성공")])

        class FakeAPIError(Exception):
            pass

        # 실제 APIError 대신, 모킹된 create가 첫 호출엔 raise (ClaudeClient가
        # except APIError로 잡으므로 동일 예외 클래스 사용 필요)
        from anthropic import APIError

        mock_messages.create.side_effect = [
            APIError("503 Service Unavailable", request=MagicMock(), body=None),
            success_resp,
        ]
        monkeypatch.setattr(
            cc_module,
            "Anthropic",
            MagicMock(return_value=SimpleNamespace(messages=mock_messages)),
        )

        client = cc_module.ClaudeClient(settings=settings, use_cache=True)
        ctx = make_ctx()

        r1 = client.explain_technical(ctx)
        assert "LLM 해석 실패" in r1

        r2 = client.explain_technical(ctx)
        assert r2 == "성공"

        assert mock_messages.create.call_count == 2, "실패는 캐시되지 않아야 함"

    def test_cache_key_stored_under_expected_prefix(self, monkeypatch):
        client, _ = make_client_with_mock_sdk(monkeypatch)
        ctx = make_ctx()
        client.explain_technical(ctx)

        key = llm_cache_key(ctx, "test-model")
        cached = get_cache().get(key)
        assert cached == "해석 결과"
