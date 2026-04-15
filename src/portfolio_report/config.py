from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_DIR = PROJECT_ROOT / "data" / "cache"
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "data" / "reports"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Naver crawling ---
    naver_concurrent_requests: int = 5
    naver_request_delay_ms: int = 300
    naver_max_retries: int = 3
    naver_timeout_sec: float = 10.0
    naver_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    # --- Cache TTLs (seconds) ---
    # 장중 가격은 짧게, 장 마감 후에는 다음 개장까지 길게 유지
    cache_price_intraday_ttl_sec: int = 300         # 5분
    cache_price_eod_ttl_sec: int = 43_200           # 12시간
    # PER/베타 등 펀더멘털은 하루에 한 번 정도만 갱신
    cache_fundamental_ttl_sec: int = 86_400         # 1일
    # 종목 마스터는 거의 변하지 않음
    cache_ticker_master_ttl_sec: int = 604_800      # 7일

    cache_dir: Path = DEFAULT_CACHE_DIR

    # --- LLM ---
    anthropic_api_key: SecretStr | None = None
    claude_model: str = "claude-sonnet-4-20250514"
    llm_max_tokens: int = 1024
    llm_temperature: float = 0.2

    # --- Output defaults ---
    default_format: Literal["console", "markdown", "html"] = "console"
    default_indicators: list[str] = Field(default_factory=list)
    reports_dir: Path = DEFAULT_REPORTS_DIR

    # --- Benchmark (for future regression use) ---
    benchmark_symbol: str = "KS11"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.cache_dir.mkdir(parents=True, exist_ok=True)
        _settings.reports_dir.mkdir(parents=True, exist_ok=True)
    return _settings
