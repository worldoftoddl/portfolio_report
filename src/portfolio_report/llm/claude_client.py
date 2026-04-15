"""Anthropic Claude API 클라이언트.

동기(`Anthropic`)와 비동기(`AsyncAnthropic`) 두 클라이언트를 함께 보관한다:
- `explain_technical`         : CLI 등 동기 경로 (messages.create)
- `explain_technical_stream`  : FastAPI SSE 경로 (messages.stream, async)

캐시 저장소는 공유된다 — 비스트리밍이 만든 결과를 스트리밍이 히트할 수 있도록
같은 `llm_cache_key`를 사용한다.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from anthropic import Anthropic, APIError, AsyncAnthropic

from portfolio_report.config import Settings, get_settings
from portfolio_report.data.cache import get_cache
from portfolio_report.llm.base import BaseLLMClient, TechnicalContext
from portfolio_report.llm.cache import llm_cache_key
from portfolio_report.llm.prompts import (
    build_technical_system_prompt,
    build_technical_user_prompt,
)

logger = logging.getLogger(__name__)


class ClaudeClient(BaseLLMClient):
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        use_cache: bool = True,
    ):
        self.settings = settings or get_settings()
        self.use_cache = use_cache
        if self.settings.anthropic_api_key is None:
            raise RuntimeError(
                "ANTHROPIC_API_KEY가 설정되지 않았습니다. .env 파일 또는 환경변수를 확인하세요."
            )
        api_key = self.settings.anthropic_api_key.get_secret_value()
        self._client = Anthropic(api_key=api_key)
        self._async_client = AsyncAnthropic(api_key=api_key)

    # --- 동기 경로 ---

    def explain_technical(self, ctx: TechnicalContext) -> str:
        cache_key = llm_cache_key(ctx, self.settings.claude_model)

        if self.use_cache:
            cached = get_cache().get(cache_key)
            if isinstance(cached, str) and cached:
                logger.info("[LLM cache hit] %s", cache_key)
                return cached

        result = self._call_claude(ctx)

        # 실패/빈 응답은 캐시하지 않음 (재시도 가능하게)
        if self.use_cache and _is_cacheable(result):
            get_cache().set(cache_key, result, expire=self.settings.cache_llm_ttl_sec)

        return result

    def _call_claude(self, ctx: TechnicalContext) -> str:
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
        parts = [
            block.text for block in response.content
            if getattr(block, "type", None) == "text"
        ]
        return "\n".join(parts).strip() or "(빈 응답)"

    # --- 스트리밍 경로 ---

    async def explain_technical_stream(
        self, ctx: TechnicalContext
    ) -> AsyncIterator[dict]:
        cache_key = llm_cache_key(ctx, self.settings.claude_model)

        # 1) 캐시 히트 → 전체 텍스트 즉시 반환 (스트리밍 없음)
        if self.use_cache:
            cached = get_cache().get(cache_key)
            if isinstance(cached, str) and cached:
                logger.info("[LLM stream cache hit] %s", cache_key)
                yield {"type": "meta", "cached": True, "text": cached}
                yield {"type": "done"}
                return

        # 2) 캐시 미스 → 실제 스트리밍
        yield {"type": "meta", "cached": False}

        system = build_technical_system_prompt()
        user = build_technical_user_prompt(ctx)
        chunks: list[str] = []
        try:
            async with self._async_client.messages.stream(
                model=self.settings.claude_model,
                max_tokens=self.settings.llm_max_tokens,
                temperature=self.settings.llm_temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            ) as stream:
                async for text in stream.text_stream:
                    chunks.append(text)
                    yield {"type": "delta", "text": text}
        except Exception as e:  # noqa: BLE001 - SDK/네트워크/취소 모두 포괄
            logger.warning("Claude 스트리밍 오류: %s", e)
            yield {"type": "error", "message": str(e)}
            # 부분 결과는 캐시 금지
            return

        # 3) 정상 완료 → 누적 텍스트를 캐시에 저장 (저장 가능 여부 검증)
        full = "".join(chunks).strip()
        if self.use_cache and _is_cacheable(full):
            get_cache().set(cache_key, full, expire=self.settings.cache_llm_ttl_sec)
        yield {"type": "done"}


def _is_cacheable(result: str) -> bool:
    """성공 응답만 캐시. 실패 문자열/빈 문자열은 스킵."""
    return bool(result) and not result.startswith("(LLM 해석 실패") and result != "(빈 응답)"
