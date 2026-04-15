"use client";

import { useLLMStream } from "@/hooks/useLLMStream";
import type { LLMExplainRequest } from "@/types/api";

interface Props {
  code: string;
  request: LLMExplainRequest;
  disabled?: boolean;
}

/**
 * 스트리밍 LLM 해석 — 사용자 클릭 시점에 SSE로 토큰 수신.
 *
 * - 캐시 히트 시 meta 이벤트의 text로 즉시 전체 표시 (isCached=true 배지)
 * - 미스 시 delta들을 append, 커서 애니메이션 노출
 * - 실패 시 메시지 + 재시도 버튼 (rate limit/타임아웃 대응)
 */
export default function LLMExplanation({ code, request, disabled }: Props) {
  const { text, isStreaming, isCached, error, start } = useLLMStream(code);

  const buttonLabel = isStreaming
    ? "해석 중..."
    : text
      ? "다시 요청"
      : "AI 해석 요청";

  return (
    <section className="rounded border border-gray-200 bg-gray-50 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-800">
          AI 해석
          {isCached && text && (
            <span className="ml-2 rounded border border-green-200 bg-green-50 px-1.5 py-0.5 text-[10px] font-normal text-green-700">
              캐시 히트
            </span>
          )}
        </h2>
        <button
          type="button"
          onClick={() => start(request)}
          disabled={disabled || isStreaming}
          className="rounded bg-purple-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-purple-700 disabled:opacity-50"
        >
          {buttonLabel}
        </button>
      </div>

      {error && (
        <div className="mb-2 flex items-center justify-between rounded border border-red-200 bg-red-50 p-2">
          <span className="text-xs text-red-700">
            해석 실패: {error.message}
          </span>
          <button
            type="button"
            onClick={() => start(request)}
            className="rounded bg-red-600 px-2 py-1 text-xs text-white hover:bg-red-700"
          >
            다시 시도
          </button>
        </div>
      )}

      {text && (
        <div className="whitespace-pre-wrap text-sm leading-6 text-gray-800">
          {text}
          {isStreaming && !isCached && (
            <span className="ml-1 inline-block h-4 w-2 animate-pulse bg-purple-400 align-middle" />
          )}
        </div>
      )}

      {!text && !error && !isStreaming && (
        <p className="text-xs text-gray-500">
          버튼을 누르면 현재 차트의 기술적 신호를 Claude가 해석합니다. 첫 토큰이
          2초 이내에 표시되며, 같은 종목을 재요청하면 캐시에서 즉시 반환됩니다.
        </p>
      )}
    </section>
  );
}
