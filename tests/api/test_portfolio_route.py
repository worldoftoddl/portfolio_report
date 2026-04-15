"""POST /api/portfolio 통합 테스트.

- `PortfolioAnalyzer`를 mock으로 교체 (네트워크 0)
- 정상/404/422 시나리오 커버
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from portfolio_report.api.app import create_app
from portfolio_report.models.holding import Holding
from portfolio_report.models.portfolio import (
    Coverage,
    Portfolio,
    PortfolioAggregates,
    PortfolioReport,
)
from portfolio_report.models.stock import StockInfo


def _sample_report() -> PortfolioReport:
    holding = Holding(
        code="005930",
        name="삼성전자",
        quantity=10,
        stock=StockInfo(
            code="005930",
            name="삼성전자",
            current_price=70000,
            per=15.0,
            forward_per=12.0,
            eps=5000.0,
            beta=1.1,
        ),
    )
    return PortfolioReport(
        generated_at=datetime(2026, 4, 15, 10, 0, 0),
        portfolio=Portfolio(holdings=[holding]),
        aggregates=PortfolioAggregates(
            weighted_per=15.0,
            weighted_forward_per=12.0,
            weighted_beta=1.1,
            per_coverage=Coverage(metric="per", included_value=700000),
            forward_per_coverage=Coverage(metric="forward_per", included_value=700000),
            beta_coverage=Coverage(metric="beta", included_value=700000),
            total_market_value=700000,
        ),
        per_stock_analyses=[],
        warnings=[],
    )


@pytest.fixture
def mock_analyzer() -> MagicMock:
    analyzer = MagicMock()
    analyzer.analyze.return_value = _sample_report()
    analyzer._price = MagicMock()
    analyzer._resolver = MagicMock()
    return analyzer


@pytest.fixture
def client(mock_analyzer) -> TestClient:
    app = create_app(analyzer=mock_analyzer)
    return TestClient(app)


class TestAnalyzePortfolio:
    def test_happy_path_returns_report(self, client, mock_analyzer):
        resp = client.post(
            "/api/portfolio",
            json={
                "holdings": [{"code": "005930", "quantity": 10}],
                "indicators": [],
                "ohlcv_days": 180,
                "use_llm": False,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["aggregates"]["weighted_per"] == 15.0
        assert body["portfolio"]["holdings"][0]["code"] == "005930"
        assert body["warnings"] == []

        # analyzer.analyze가 올바른 인자로 호출됐는지
        mock_analyzer.analyze.assert_called_once()
        call_args = mock_analyzer.analyze.call_args
        # positional or keyword 모두 허용
        inputs = call_args.args[0] if call_args.args else call_args.kwargs["inputs"]
        assert inputs[0].code == "005930"

    def test_missing_holdings_returns_422(self, client):
        resp = client.post("/api/portfolio", json={"holdings": []})
        assert resp.status_code == 422

    def test_invalid_indicator_returns_400(self, client):
        resp = client.post(
            "/api/portfolio",
            json={
                "holdings": [{"code": "005930", "quantity": 10}],
                "indicators": ["bogus"],
            },
        )
        assert resp.status_code == 400
        assert resp.json()["error"] == "invalid_indicator"

    def test_analyzer_value_error_maps_to_404(self, client, mock_analyzer):
        mock_analyzer.analyze.side_effect = ValueError("종목명 '없는종목'을(를) 찾을 수 없습니다")
        resp = client.post(
            "/api/portfolio",
            json={"holdings": [{"name": "없는종목", "quantity": 1}]},
        )
        assert resp.status_code == 404
        assert resp.json()["error"] == "ticker_not_found"
