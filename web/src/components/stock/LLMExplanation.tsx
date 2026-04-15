"use client";

import { useLLMExplain } from "@/hooks/useLLMExplain";
import type { LLMExplainRequest } from "@/types/api";

interface Props {
  code: string;
  request: LLMExplainRequest;
  disabled?: boolean;
}

/**
 * 사용자 클릭 시점에만 `POST /api/stock/{code}/llm-explain` 호출.
 * mutation이라 자동 재실행 없음 — 리프레시/언마운트로 안전히 폐기.
 */
export default function LLMExplanation({ code, request, disabled }: Props) {
  const mutation = useLLMExplain(code);

  return (
    <section className="rounded border border-gray-200 bg-gray-50 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-800">AI 해석</h2>
        <button
          type="button"
          onClick={() => mutation.mutate(request)}
          disabled={disabled || mutation.isPending}
          className="rounded bg-purple-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-purple-700 disabled:opacity-50"
        >
          {mutation.isPending
            ? "해석 중..."
            : mutation.data
              ? "다시 요청"
              : "AI 해석 요청"}
        </button>
      </div>

      {mutation.error && (
        <p className="text-xs text-red-700">
          해석 실패: {mutation.error.message}
        </p>
      )}

      {mutation.data && (
        <div className="whitespace-pre-wrap text-sm leading-6 text-gray-800">
          {mutation.data.explanation}
        </div>
      )}

      {!mutation.data && !mutation.error && !mutation.isPending && (
        <p className="text-xs text-gray-500">
          버튼을 누르면 현재 차트의 기술적 신호를 Claude가 해석합니다.
          토큰 사용이 있으므로 필요할 때만 호출하십시오.
        </p>
      )}
    </section>
  );
}
