"""Anthropic Claude API 클라이언트."""

from __future__ import annotations

import logging

from anthropic import Anthropic, APIError

from portfolio_report.config import Settings, get_settings
from portfolio_report.llm.base import BaseLLMClient, TechnicalContext
from portfolio_report.llm.prompts import (
    build_technical_system_prompt,
    build_technical_user_prompt,
)

logger = logging.getLogger(__name__)


class ClaudeClient(BaseLLMClient):
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        if self.settings.anthropic_api_key is None:
            raise RuntimeError(
                "ANTHROPIC_API_KEY가 설정되지 않았습니다. .env 파일 또는 환경변수를 확인하세요."
            )
        self._client = Anthropic(api_key=self.settings.anthropic_api_key.get_secret_value())

    def explain_technical(self, ctx: TechnicalContext) -> str:
        system = build_technical_system_prompt()
        user = build_technical_user_prompt(ctx)
        try:
            response = self._client.messages.create(
                model=self.settings.claude_model,
                max_tokens=self.settings.llm_max_tokens,
                temperature=self.settings.llm_temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except APIError as e:
            logger.warning("Claude API 오류: %s", e)
            return f"(LLM 해석 실패: {e})"
        # SDK는 content 리스트 (text blocks)를 반환
        parts = [
            block.text for block in response.content
            if getattr(block, "type", None) == "text"
        ]
        return "\n".join(parts).strip() or "(빈 응답)"
