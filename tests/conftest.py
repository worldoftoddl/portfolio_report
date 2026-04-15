from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def read_fixture(fixtures_dir):
    def _read(relative: str) -> str:
        return (fixtures_dir / relative).read_text(encoding="utf-8")

    return _read
