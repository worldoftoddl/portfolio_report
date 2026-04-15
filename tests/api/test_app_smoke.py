"""앱 팩토리 스모크 테스트.

실제 lifespan(NaverClient 생성 → 네트워크)은 타지 않는다.
팩토리 호출만으로 라우트/핸들러/세마포어 등이 올바르게 조립되는지 확인.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI

from portfolio_report.api.app import create_app


def test_create_app_without_args_returns_app_with_lifespan():
    app = create_app()
    assert isinstance(app, FastAPI)
    assert app.router.lifespan_context is not None

    paths = {route.path for route in app.routes}
    assert "/api/portfolio" in paths
    assert "/api/stock/{code}/ohlcv" in paths
    assert "/api/stock/{code}/llm-explain" in paths


def test_create_app_with_mock_analyzer_skips_lifespan():
    app = create_app(analyzer=MagicMock(_price=MagicMock(), _resolver=MagicMock()))
    assert app.state.analyzer is not None
    # 세마포어는 양쪽 경로 모두 설정됨
    assert app.state.naver_semaphore is not None


def test_cors_origins_applied():
    app = create_app(analyzer=MagicMock(_price=MagicMock(), _resolver=MagicMock()))
    # CORSMiddleware가 미들웨어 스택에 포함됨
    mw_names = [mw.cls.__name__ for mw in app.user_middleware]
    assert "CORSMiddleware" in mw_names
