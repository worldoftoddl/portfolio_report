"""NaverClient 통합 테스트 (pytest-vcr 카세트 기반).

목적:
- HTTP 계층 + 파서 결합을 실제 네이버 응답으로 검증
- 카세트가 stale해지면(네이버 HTML 구조 변경) 파서가 먼저 실패 → 조기 감지
- CI/회귀 검증은 PORTFOLIO_REPORT_VCR_RECORD=none (기본)로 카세트만 재생

카세트 녹화 방법:
    PORTFOLIO_REPORT_VCR_RECORD=new_episodes uv run pytest tests/data/test_naver_client_vcr.py

또는 전체 갱신:
    ./scripts/refresh_cassettes.sh
"""

from __future__ import annotations

import pytest

from portfolio_report.data.naver_client import NaverClient

# 대표 종목 1개로 제한 (카세트 크기 관리)
SAMPLE_CODE = "005930"  # 삼성전자


@pytest.mark.vcr()
def test_fetch_snapshot_returns_expected_fields():
    with NaverClient() as client:
        result = client.fetch_snapshot(SAMPLE_CODE)
    assert result["code"] == SAMPLE_CODE
    assert result["name"]  # 비어있지 않음
    assert isinstance(result["current_price"], float)
    assert result["current_price"] > 0
    assert isinstance(result["market_cap"], float)
    assert result["market_cap"] > 0


@pytest.mark.vcr()
def test_fetch_main_info_returns_per_and_eps():
    with NaverClient() as client:
        result = client.fetch_main_info(SAMPLE_CODE)
    # PER/EPS는 항상 존재 (삼성전자 같은 대형주 기준)
    assert result.get("per") is not None
    assert result.get("eps") is not None
    # 타입 검증
    assert isinstance(result["per"], float)
    assert isinstance(result["eps"], float)


@pytest.mark.vcr()
def test_fetch_wisereport_returns_beta():
    with NaverClient() as client:
        result = client.fetch_wisereport(SAMPLE_CODE)
    assert result.get("beta") is not None
    assert isinstance(result["beta"], float)
    # 베타는 음수/0이 될 수도 있지만 상식적 범위 내
    assert -2.0 < result["beta"] < 5.0
