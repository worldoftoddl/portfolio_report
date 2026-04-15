"""네이버 호출 경로 세마포어 의존성 테스트.

- 네이버를 쓰는 엔드포인트(`POST /api/portfolio`, `GET /api/stock/{code}/ohlcv`)
  에만 적용 — `POST /api/stock/{code}/llm-explain`(Claude)은 블로킹되지 않음.
- `app.state.naver_semaphore`에 앱 레벨 싱글톤을 저장하고 요청마다 획득/해제.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from portfolio_report.api.app import create_app
from portfolio_report.api.deps import (
    acquire_naver_semaphore,
    get_llm_client,
    get_price_client,
    get_resolver,
)
from portfolio_report.data.ticker_resolver import ResolvedTicker
from portfolio_report.models.holding import Holding
from portfolio_report.models.portfolio import (
    Coverage,
    Portfolio,
    PortfolioAggregates,
    PortfolioReport,
)


@pytest.fixture
def slow_analyzer() -> MagicMock:
    """analyze()가 0.2초 블로킹 (세마포어 대기 관측용)."""
    import time

    def slow_analyze(*args, **kwargs):
        time.sleep(0.2)
        return PortfolioReport(
            generated_at=__import__("datetime").datetime.now(),
            portfolio=Portfolio(
                holdings=[Holding(code="005930", name="삼성전자", quantity=1)]
            ),
            aggregates=PortfolioAggregates(
                per_coverage=Coverage(metric="per"),
                forward_per_coverage=Coverage(metric="forward_per"),
                beta_coverage=Coverage(metric="beta"),
            ),
        )

    a = MagicMock()
    a.analyze.side_effect = slow_analyze
    a._price = MagicMock()
    a._resolver = MagicMock()
    return a


class TestSemaphoreDependencyWiring:
    def test_app_state_has_semaphore(self):
        app = create_app(analyzer=MagicMock(_price=MagicMock(), _resolver=MagicMock()))
        sem = app.state.naver_semaphore
        assert isinstance(sem, asyncio.Semaphore)

    def test_llm_explain_route_does_not_acquire_naver_semaphore(self, slow_analyzer):
        """LLM 엔드포인트는 세마포어를 건드리지 않아야 한다."""
        llm = MagicMock()
        llm.explain_technical.return_value = "ok"
        app = create_app(
            analyzer=slow_analyzer,
            price_client=slow_analyzer._price,
            resolver=slow_analyzer._resolver,
            llm_client=llm,
        )
        app.dependency_overrides[get_llm_client] = lambda: llm

        acquired: list[bool] = []

        async def spy_dep():
            acquired.append(True)

        app.dependency_overrides[acquire_naver_semaphore] = spy_dep
        client = TestClient(app)
        resp = client.post(
            "/api/stock/005930/llm-explain",
            json={"name": "삼성전자"},
        )
        assert resp.status_code == 200
        # LLM 경로에는 acquire가 바인딩되지 않았으므로 spy는 호출되지 않음
        assert acquired == []


@pytest.mark.anyio
class TestSemaphoreLimitInAction:
    """limit=1일 때 두 번째 요청이 첫 번째 완료까지 대기하는지 실측 검증."""

    @pytest.fixture
    def anyio_backend(self):
        return "asyncio"

    async def test_concurrent_portfolio_requests_serialize(self, slow_analyzer):
        app = create_app(
            analyzer=slow_analyzer,
            price_client=slow_analyzer._price,
            resolver=slow_analyzer._resolver,
        )
        # 한도를 1로 강제 → 동시 2개 요청은 0.2s + 0.2s = 0.4s 이상
        app.state.naver_semaphore = asyncio.Semaphore(1)

        payload = {
            "holdings": [{"code": "005930", "quantity": 1}],
            "use_llm": False,
        }
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            start = asyncio.get_event_loop().time()
            r1, r2 = await asyncio.gather(
                ac.post("/api/portfolio", json=payload),
                ac.post("/api/portfolio", json=payload),
            )
            elapsed = asyncio.get_event_loop().time() - start

        assert r1.status_code == 200
        assert r2.status_code == 200
        # 두 요청이 직렬화되면 0.4s 근처, 병렬이면 0.2s 근처
        assert elapsed >= 0.35, f"세마포어가 직렬화하지 않음 (elapsed={elapsed:.3f}s)"


class TestOhlcvAlsoGated:
    """/api/stock/{code}/ohlcv도 네이버 폴백에 걸린 FDR 사용 → 세마포어 대상."""

    def test_ohlcv_route_uses_naver_semaphore(self):
        price = MagicMock()
        idx = pd.date_range("2026-01-05", periods=40, freq="B")
        price.get_ohlcv.return_value = pd.DataFrame(
            {
                "Open": [100.0] * 40,
                "High": [101.0] * 40,
                "Low": [99.0] * 40,
                "Close": [100.5] * 40,
                "Volume": [1000] * 40,
            },
            index=idx,
        )
        resolver = MagicMock()
        resolver.resolve.return_value = ResolvedTicker(
            code="005930", name="삼성전자", warnings=[]
        )
        analyzer = MagicMock(_price=price, _resolver=resolver)
        app = create_app(analyzer=analyzer, price_client=price, resolver=resolver)

        calls: list[str] = []

        async def spy_dep():
            calls.append("acquired")

        app.dependency_overrides[acquire_naver_semaphore] = spy_dep
        app.dependency_overrides[get_price_client] = lambda: price
        app.dependency_overrides[get_resolver] = lambda: resolver

        client = TestClient(app)
        resp = client.get("/api/stock/005930/ohlcv")
        assert resp.status_code == 200
        assert calls == ["acquired"]
