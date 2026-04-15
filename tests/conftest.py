from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
CASSETTES_DIR = Path(__file__).parent / "cassettes"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def read_fixture(fixtures_dir):
    def _read(relative: str) -> str:
        return (fixtures_dir / relative).read_text(encoding="utf-8")

    return _read


@pytest.fixture(scope="module")
def vcr_config():
    """pytest-vcr 기본 설정.

    - 민감 헤더(쿠키/인증) 필터링
    - 매칭은 method + scheme + host + path + query (순서 무관)
    - record_mode는 로컬 실행 시 'new_episodes'(누락된 호출만 녹화),
      CI/회귀 검증 시 'none'(카세트만 재생) — PORTFOLIO_REPORT_VCR_RECORD 환경변수로 제어
    """
    import os

    mode = os.environ.get("PORTFOLIO_REPORT_VCR_RECORD", "none")
    return {
        "record_mode": mode,
        "match_on": ["method", "scheme", "host", "path", "query"],
        "filter_headers": [
            ("Cookie", "REDACTED"),
            ("Set-Cookie", "REDACTED"),
            ("Authorization", "REDACTED"),
            ("User-Agent", "REDACTED"),
        ],
        "cassette_library_dir": str(CASSETTES_DIR),
        "decode_compressed_response": True,
    }
