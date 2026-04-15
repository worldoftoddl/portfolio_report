"""LLM 클라이언트 추상 기반.

Claude 외 다른 제공자(OpenAI/Gemini 등)로 확장할 수 있도록 인터페이스만 정의.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass(frozen=True)
class TechnicalContext:
    """기술적 분석 해석 요청용 컨텍스트."""

    code: str
    name: str
    current_price: float | None
    signals: dict  # technical._summarize 출력 (지표별 dict of dicts)
    price_tail: list[dict]  # 최근 N일 OHLCV (dict 리스트)


class BaseLLMClient(ABC):
    """LLM 클라이언트 공통 인터페이스."""

    @abstractmethod
    def explain_technical(self, ctx: TechnicalContext) -> str:
        """종목의 기술적 지표를 해석하는 한국어 문단을 반환."""

    async def explain_technical_stream(
        self, ctx: TechnicalContext
    ) -> AsyncIterator[dict]:
        """토큰 단위 스트리밍. 기본 구현은 비스트리밍 결과를 한 번에 래핑.

        이벤트 프로토콜:
            {"type": "meta", "cached": bool, "text"?: str}  ← 최초 1회
            {"type": "delta", "text": str}                    ← N회 (캐시 미스 시)
            {"type": "done"}                                  ← 정상 종료
            {"type": "error", "message": str}                 ← 실패 종료

        캐시 히트 시 meta 이벤트에 text 전체가 포함되며 delta는 발생하지 않는다.
        """
        text = await asyncio.to_thread(self.explain_technical, ctx)
        yield {"type": "meta", "cached": False, "text": text}
        yield {"type": "done"}
