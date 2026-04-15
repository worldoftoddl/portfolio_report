"""네이버 증권 비공식 엔드포인트 HTTP 클라이언트.

- 동기 httpx.Client 사용 (MVP). 추후 AsyncNaverClient로 확장 가능.
- 재시도 + 지수 백오프 + 동시 요청 제한
- 파싱은 naver_parser 모듈에 위임
"""

from __future__ import annotations

import logging
import threading
import time

import httpx

from portfolio_report.config import Settings, get_settings
from portfolio_report.data.naver_parser import (
    MainInfoResult,
    SnapshotResult,
    WisereportResult,
    parse_main_info,
    parse_snapshot,
    parse_wisereport,
)

logger = logging.getLogger(__name__)

_SNAPSHOT_URL = "https://polling.finance.naver.com/api/realtime/domestic/stock/{code}"
_MAIN_URL = "https://finance.naver.com/item/main.naver"
_WISEREPORT_URL = "https://navercomp.wisereport.co.kr/v2/company/c1010001.aspx"


class NaverClient:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._sem = threading.Semaphore(self.settings.naver_concurrent_requests)
        self._client = httpx.Client(
            timeout=self.settings.naver_timeout_sec,
            headers={
                "User-Agent": self.settings.naver_user_agent,
                "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
                "Referer": "https://finance.naver.com/",
            },
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> NaverClient:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # --- Public methods ---

    def fetch_snapshot(self, code: str) -> SnapshotResult:
        payload = self._get_json(_SNAPSHOT_URL.format(code=code))
        return parse_snapshot(payload)

    def fetch_main_info(self, code: str) -> MainInfoResult:
        html = self._get_text(_MAIN_URL, params={"code": code})
        return parse_main_info(html)

    def fetch_wisereport(self, code: str) -> WisereportResult:
        html = self._get_text(_WISEREPORT_URL, params={"cmp_cd": code})
        return parse_wisereport(html)

    # --- Internal helpers ---

    def _get_text(self, url: str, params: dict | None = None) -> str:
        return self._request(url, params=params).text

    def _get_json(self, url: str, params: dict | None = None) -> dict:
        return self._request(url, params=params).json()

    def _request(self, url: str, params: dict | None = None) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(1, self.settings.naver_max_retries + 1):
            with self._sem:
                try:
                    resp = self._client.get(url, params=params)
                    resp.raise_for_status()
                    time.sleep(self.settings.naver_request_delay_ms / 1000)
                    return resp
                except httpx.HTTPError as e:
                    last_exc = e
                    logger.warning(
                        "네이버 요청 실패 (attempt %d/%d) %s: %s",
                        attempt,
                        self.settings.naver_max_retries,
                        url,
                        e,
                    )
                    time.sleep(0.5 * (2 ** (attempt - 1)))
        raise RuntimeError(f"네이버 요청 최종 실패: {url}") from last_exc
