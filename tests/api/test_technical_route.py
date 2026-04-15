"""/api/stock/{code}/* 통합 테스트.

- resolver, price_client, llm_client 전부 mock (네트워크 0)
- Lightweight Charts 포맷 응답 검증은 serializers 테스트에서 커버 완료 →
  여기선 라우트 계약 (상태코드 + 구조 키)만 검증.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from portfolio_report.api.app import create_app
from portfolio_report.api.deps import get_llm_client, get_price_client, get_resolver
from portfolio_report.data.ticker_resolver import ResolvedTicker


@pytest.fixture
def mock_price_client() -> MagicMock:
    pc = MagicMock()
    n = 40  # BB(20)/RSI(14) 모두 일부 유효값 확보
    idx = pd.date_range("2026-01-05", periods=n, freq="B")
    df = pd.DataFrame(
        {
            "Open": [100.0 + i for i in range(n)],
            "High": [105.0 + i for i in range(n)],
            "Low": [99.0 + i for i in range(n)],
            "Close": [104.0 + i for i in range(n)],
            "Volume": [1000 + i for i in range(n)],
        },
        index=idx,
    )
    pc.get_ohlcv.return_value = df
    return pc


@pytest.fixture
def mock_resolver() -> MagicMock:
    r = MagicMock()
    r.resolve.return_value = ResolvedTicker(code="005930", name="삼성전자", warnings=[])
    return r


@pytest.fixture
def mock_llm() -> MagicMock:
    llm = MagicMock()
    llm.explain_technical.return_value = "해석 문단입니다."
    return llm


@pytest.fixture
def mock_analyzer(mock_price_client, mock_resolver) -> MagicMock:
    a = MagicMock()
    a._price = mock_price_client
    a._resolver = mock_resolver
    return a


@pytest.fixture
def client(mock_analyzer, mock_price_client, mock_resolver, mock_llm) -> TestClient:
    app = create_app(
        analyzer=mock_analyzer,
        price_client=mock_price_client,
        resolver=mock_resolver,
        llm_client=mock_llm,
    )
    # DI 오버라이드
    app.dependency_overrides[get_price_client] = lambda: mock_price_client
    app.dependency_overrides[get_resolver] = lambda: mock_resolver
    app.dependency_overrides[get_llm_client] = lambda: mock_llm
    return TestClient(app)


class TestOhlcvEndpoint:
    def test_happy_path_returns_ohlcv_series(self, client):
        resp = client.get("/api/stock/005930/ohlcv?days=30")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == "005930"
        assert body["name"] == "삼성전자"
        assert len(body["series"]["ohlcv"]) == 40
        assert body["series"]["ohlcv"][0]["time"] == "2026-01-05"
        assert body["series"]["indicators"] == {}

    def test_with_indicators_emits_series(self, client):
        resp = client.get("/api/stock/005930/ohlcv?days=30&indicators=rsi&indicators=bb")
        assert resp.status_code == 200
        indicators = resp.json()["series"]["indicators"]
        # pandas-ta가 30일 데이터론 RSI/BB 대부분 NaN → 빈 배열일 수 있지만 키는 존재
        assert "rsi" in indicators
        assert "bb" in indicators

    def test_unknown_indicator_returns_400(self, client):
        resp = client.get("/api/stock/005930/ohlcv?indicators=bogus")
        assert resp.status_code == 400
        assert resp.json()["error"] == "invalid_indicator"

    def test_resolver_value_error_maps_to_404(self, client, mock_resolver):
        mock_resolver.resolve.side_effect = ValueError("종목코드 999999을(를) 찾을 수 없습니다")
        resp = client.get("/api/stock/999999/ohlcv")
        assert resp.status_code == 404
        assert resp.json()["error"] == "ticker_not_found"

    def test_price_fetch_failure_maps_to_503(self, client, mock_price_client):
        mock_price_client.get_ohlcv.side_effect = RuntimeError("FDR down")
        resp = client.get("/api/stock/005930/ohlcv")
        assert resp.status_code == 503
        assert resp.json()["error"] == "upstream_unavailable"


class TestLLMExplainEndpoint:
    def test_happy_path_returns_explanation(self, client, mock_llm):
        resp = client.post(
            "/api/stock/005930/llm-explain",
            json={
                "name": "삼성전자",
                "current_price": 70000,
                "signals": {"rsi": {"value": 55, "signal": "중립 (55.0)"}},
                "price_tail": [],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == "005930"
        assert body["explanation"] == "해석 문단입니다."
        mock_llm.explain_technical.assert_called_once()
        ctx = mock_llm.explain_technical.call_args.args[0]
        assert ctx.code == "005930"
        assert ctx.current_price == 70000

    def test_llm_unavailable_returns_503(self, mock_analyzer, mock_price_client, mock_resolver):
        app = create_app(
            analyzer=mock_analyzer,
            price_client=mock_price_client,
            resolver=mock_resolver,
            # llm_client 미주입 → get_llm_client == None
        )
        app.dependency_overrides[get_llm_client] = lambda: None
        c = TestClient(app)
        resp = c.post(
            "/api/stock/005930/llm-explain",
            json={"name": "삼성전자"},
        )
        assert resp.status_code == 503
        assert resp.json()["error"] == "llm_unavailable"

    def test_llm_failure_returns_502(self, client, mock_llm):
        mock_llm.explain_technical.side_effect = RuntimeError("Claude timeout")
        resp = client.post(
            "/api/stock/005930/llm-explain",
            json={"name": "삼성전자"},
        )
        assert resp.status_code == 502
        assert resp.json()["error"] == "llm_failure"
