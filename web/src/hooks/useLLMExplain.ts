"use client";

import { useMutation } from "@tanstack/react-query";

import type { LLMExplainRequest, LLMExplainResponse } from "@/types/api";

/**
 * `POST /api/stock/{code}/llm-explain` — 해석은 사용자 클릭 시점에만 호출.
 *
 * 비싼 외부 호출이므로 mutation으로 두고(자동 재실행 없음), 결과는 컴포넌트
 * 내 state로만 보관. 6f 스트리밍 전환 시 본 훅을 스트리밍 버전으로 교체.
 */
export function useLLMExplain(code: string) {
  return useMutation({
    mutationFn: async (req: LLMExplainRequest): Promise<LLMExplainResponse> => {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      if (!apiUrl) {
        throw new Error("NEXT_PUBLIC_API_URL이 설정되지 않았습니다.");
      }
      const res = await fetch(`${apiUrl}/api/stock/${code}/llm-explain`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
      });
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`HTTP ${res.status}: ${body}`);
      }
      return (await res.json()) as LLMExplainResponse;
    },
  });
}
