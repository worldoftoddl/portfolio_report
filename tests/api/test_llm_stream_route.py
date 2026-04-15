"""POST /api/stock/{code}/llm-explain/stream — SSE 스트리밍 라우트.

TestClient는 streaming body를 한 번에 수신하므로 스트림 이벤트 순서와 포맷을
`data:` 라인 단위로 파싱해 검증한다.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from portfolio_report.api.app import create_app
from portfolio_report.api.deps import get_llm_client


class _FakeStreamingLLM:
    """explain_technical_stream을 이벤트 리스트로 흉내내는 스텁."""

    def __init__(self, events: list[dict]):
        self._events = events
        self.explain_technical_calls: list = []

    def explain_technical(self, ctx):  # 비스트리밍 API 인터페이스 유지
        self.explain_technical_calls.append(ctx)
        return "sync result"

    async def explain_technical_stream(self, ctx):
        for ev in self._events:
            yield ev


def _make_client(llm) -> TestClient:
    analyzer = MagicMock(_price=MagicMock(), _resolver=MagicMock())
    app = create_app(analyzer=analyzer, llm_client=llm)
    app.dependency_overrides[get_llm_client] = lambda: llm
    return TestClient(app)


def _parse_sse(body: str) -> list[dict]:
    events = []
    for block in body.split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: ") :]))
    return events


class TestSSEStream:
    def test_cache_miss_emits_meta_deltas_done(self):
        llm = _FakeStreamingLLM(
            [
                {"type": "meta", "cached": False},
                {"type": "delta", "text": "첫 "},
                {"type": "delta", "text": "토큰"},
                {"type": "done"},
            ]
        )
        client = _make_client(llm)
        resp = client.post(
            "/api/stock/005930/llm-explain/stream",
            json={"name": "삼성전자"},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

        events = _parse_sse(resp.text)
        assert events[0] == {"type": "meta", "cached": False}
        assert [e["text"] for e in events if e["type"] == "delta"] == ["첫 ", "토큰"]
        assert events[-1] == {"type": "done"}

    def test_cache_hit_emits_single_meta_with_full_text(self):
        llm = _FakeStreamingLLM(
            [
                {"type": "meta", "cached": True, "text": "전체 캐시 해석"},
                {"type": "done"},
            ]
        )
        client = _make_client(llm)
        resp = client.post(
            "/api/stock/005930/llm-explain/stream",
            json={"name": "삼성전자"},
        )
        events = _parse_sse(resp.text)
        assert events[0]["cached"] is True
        assert events[0]["text"] == "전체 캐시 해석"
        assert not any(e["type"] == "delta" for e in events)

    def test_error_event_propagated(self):
        llm = _FakeStreamingLLM(
            [
                {"type": "meta", "cached": False},
                {"type": "delta", "text": "부분"},
                {"type": "error", "message": "connection dropped"},
            ]
        )
        client = _make_client(llm)
        resp = client.post(
            "/api/stock/005930/llm-explain/stream",
            json={"name": "삼성전자"},
        )
        events = _parse_sse(resp.text)
        assert any(e["type"] == "error" for e in events)

    def test_llm_unavailable_returns_503(self):
        analyzer = MagicMock(_price=MagicMock(), _resolver=MagicMock())
        app = create_app(analyzer=analyzer)
        app.dependency_overrides[get_llm_client] = lambda: None
        c = TestClient(app)
        resp = c.post(
            "/api/stock/005930/llm-explain/stream",
            json={"name": "삼성전자"},
        )
        assert resp.status_code == 503
        assert resp.json()["error"] == "llm_unavailable"
