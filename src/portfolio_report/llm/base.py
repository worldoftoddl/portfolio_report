"""LLM 클라이언트 추상 기반.

Claude 외 다른 제공자(OpenAI/Gemini 등)로 확장할 수 있도록 인터페이스만 정의.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
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
