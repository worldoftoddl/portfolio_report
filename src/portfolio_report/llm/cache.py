"""LLM 응답 캐시 헬퍼 (순수 함수).

키 설계:
    llm:{model}:{code}:{date_kst}:{signals_hash}

- date_kst: KST 기준 YYYY-MM-DD (장 마감 후 재실행 시 재사용)
- signals_hash: signals dict을 정렬 JSON 직렬화 후 SHA1 앞 12자리
  (같은 날짜라도 장중 신호가 바뀌면 다른 키 → stale 방지)
- price_tail은 키 결정에서 제외 (참고용 컨텍스트)
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from portfolio_report.llm.base import TechnicalContext

_KST = ZoneInfo("Asia/Seoul")


def signals_hash(signals: dict) -> str:
    """signals dict을 안정적으로 직렬화한 뒤 SHA1 앞 12자리(hex)."""
    serialized = json.dumps(signals, sort_keys=True, ensure_ascii=False, default=str)
    digest = hashlib.sha1(serialized.encode("utf-8")).hexdigest()
    return digest[:12]


def llm_cache_key(
    ctx: TechnicalContext,
    model: str,
    now: datetime | None = None,
) -> str:
    if now is None:
        now = datetime.now(tz=_KST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=_KST)
    date_kst = now.astimezone(_KST).strftime("%Y-%m-%d")
    return f"llm:{model}:{ctx.code}:{date_kst}:{signals_hash(ctx.signals)}"
