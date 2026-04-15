"""ClaudeClient.explain_technical_stream 단위 테스트.

AsyncAnthropic.messages.stream은 async context manager + text_stream async
iterator. 실제 SDK 호출은 피하고 테스트용 async mock으로 교체.

이벤트 프로토콜:
    meta (cached=true|false) → [delta × N] → done
    또는
    meta → [delta × 부분] → error (완료 시 캐시 저장 금지)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from portfolio_report.config import Settings
from portfolio_report.llm.base import TechnicalContext
from portfolio_report.llm.claude_client import ClaudeClient


pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def settings(tmp_path):
    return Settings(
        anthropic_api_key="sk-fake-test",  # pydantic SecretStr 수용
        cache_dir=tmp_path / "cache",
    )


@pytest.fixture(autouse=True)
def clear_llm_cache():
    """llm: prefix 키만 비워 테스트 간 격리."""
    from portfolio_report.data.cache import get_cache

    cache = get_cache()
    for key in list(cache):
        if isinstance(key, str) and key.startswith("llm:"):
            cache.delete(key)
    yield
    for key in list(cache):
        if isinstance(key, str) and key.startswith("llm:"):
            cache.delete(key)


@pytest.fixture
def ctx():
    return TechnicalContext(
        code="005930",
        name="삼성전자",
        current_price=70000,
        signals={"rsi": {"value": 55, "signal": "중립 (55.0)"}},
        price_tail=[],
    )


def _async_iter(items):
    """리스트를 async iterator로 변환."""

    async def gen():
        for it in items:
            yield it

    return gen()


class _AsyncStreamCtx:
    """AsyncMessageStreamManager 스텁.

    async with client.messages.stream(...) as stream:
        async for text in stream.text_stream: ...
    패턴을 흉내.
    """

    def __init__(self, chunks: list[str], raise_in_text: Exception | None = None):
        self._chunks = chunks
        self._raise = raise_in_text

    async def __aenter__(self):
        stream = MagicMock()
        if self._raise is None:
            stream.text_stream = _async_iter(self._chunks)
        else:
            async def _raising():
                for c in self._chunks:
                    yield c
                raise self._raise

            stream.text_stream = _raising()
        return stream

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


def _patched_client(settings, stream_ctx: _AsyncStreamCtx) -> ClaudeClient:
    with patch("portfolio_report.llm.claude_client.Anthropic") as mock_sync, patch(
        "portfolio_report.llm.claude_client.AsyncAnthropic"
    ) as mock_async:
        mock_sync.return_value = MagicMock()
        async_client = MagicMock()
        async_client.messages.stream = MagicMock(return_value=stream_ctx)
        mock_async.return_value = async_client
        return ClaudeClient(settings=settings)


async def _collect(stream) -> list[dict[str, Any]]:
    return [ev async for ev in stream]


class TestStreamBasics:
    async def test_cache_miss_yields_meta_deltas_done(self, settings, ctx):
        """캐시 미스 시: meta(cached=false) → delta × N → done 순서로 이벤트 발생."""
        client = _patched_client(
            settings, _AsyncStreamCtx(["첫 ", "토큰 ", "테스트입니다."])
        )
        events = await _collect(client.explain_technical_stream(ctx))

        assert events[0] == {"type": "meta", "cached": False}
        deltas = [e for e in events if e["type"] == "delta"]
        assert [d["text"] for d in deltas] == ["첫 ", "토큰 ", "테스트입니다."]
        assert events[-1] == {"type": "done"}

    async def test_cache_hit_yields_full_text_immediately(self, settings, ctx):
        """캐시 히트 시: meta(cached=true, text=전체) + done, delta 없음."""
        client = _patched_client(settings, _AsyncStreamCtx([]))  # SDK 호출 없음
        from portfolio_report.data.cache import get_cache
        from portfolio_report.llm.cache import llm_cache_key

        key = llm_cache_key(ctx, settings.claude_model)
        get_cache().set(key, "캐시된 전체 해석")

        events = await _collect(client.explain_technical_stream(ctx))

        assert events[0]["type"] == "meta"
        assert events[0]["cached"] is True
        assert events[0]["text"] == "캐시된 전체 해석"
        assert events[-1] == {"type": "done"}
        assert not any(e["type"] == "delta" for e in events)

    async def test_successful_stream_stores_to_cache(self, settings, ctx):
        """완료된 스트림은 누적 텍스트를 캐시에 저장."""
        client = _patched_client(
            settings, _AsyncStreamCtx(["hello ", "world"])
        )
        _ = await _collect(client.explain_technical_stream(ctx))

        from portfolio_report.data.cache import get_cache
        from portfolio_report.llm.cache import llm_cache_key

        key = llm_cache_key(ctx, settings.claude_model)
        assert get_cache().get(key) == "hello world"


class TestFailureDoesNotCache:
    async def test_exception_mid_stream_emits_error_event_and_no_cache(
        self, settings, ctx
    ):
        """스트리밍 중 예외 → error 이벤트 방출, 캐시 저장 금지."""
        client = _patched_client(
            settings,
            _AsyncStreamCtx(["partial "], raise_in_text=RuntimeError("connection dropped")),
        )
        events = await _collect(client.explain_technical_stream(ctx))

        assert any(e["type"] == "error" for e in events)
        assert "connection dropped" in next(
            e["message"] for e in events if e["type"] == "error"
        )

        from portfolio_report.data.cache import get_cache
        from portfolio_report.llm.cache import llm_cache_key

        key = llm_cache_key(ctx, settings.claude_model)
        assert get_cache().get(key) is None, "실패한 스트림은 캐시에 저장되면 안 됨"

    async def test_empty_stream_does_not_cache(self, settings, ctx):
        """빈 응답은 (빈 응답) 문자열도 캐시하지 않음."""
        client = _patched_client(settings, _AsyncStreamCtx([]))
        _ = await _collect(client.explain_technical_stream(ctx))

        from portfolio_report.data.cache import get_cache
        from portfolio_report.llm.cache import llm_cache_key

        key = llm_cache_key(ctx, settings.claude_model)
        assert get_cache().get(key) is None


class TestCacheSharedWithNonStreaming:
    async def test_non_streaming_result_is_reused_by_stream(self, settings, ctx):
        """기존 비스트리밍 `explain_technical`로 캐시된 결과를
        스트리밍 엔드포인트가 cache hit으로 인식해야 한다 (키 공유)."""
        from portfolio_report.data.cache import get_cache
        from portfolio_report.llm.cache import llm_cache_key

        key = llm_cache_key(ctx, settings.claude_model)
        get_cache().set(key, "비스트리밍으로 먼저 만든 결과")

        client = _patched_client(settings, _AsyncStreamCtx(["SHOULD_NOT_BE_CALLED"]))
        events = await _collect(client.explain_technical_stream(ctx))

        assert events[0]["cached"] is True
        assert events[0]["text"] == "비스트리밍으로 먼저 만든 결과"
