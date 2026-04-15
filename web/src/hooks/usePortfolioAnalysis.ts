"use client";

import { useMutation } from "@tanstack/react-query";

import type { PortfolioAnalyzeRequest, PortfolioReport } from "@/types/api";

/**
 * `POST /api/portfolio` 호출. `useMutation`은 부수 효과가 있는 요청에 적합.
 *
 * 성공한 응답은 캐시하지 않는다 (쿼리 훅이 아님). 결과를 라우팅 가능한
 * 캐시 키로 보관하려면 6e-4에서 `queryClient.setQueryData`로 삽입 예정.
 */
export function usePortfolioAnalysis() {
  return useMutation({
    mutationFn: async (
      req: PortfolioAnalyzeRequest,
    ): Promise<PortfolioReport> => {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      if (!apiUrl) {
        throw new Error(
          "NEXT_PUBLIC_API_URL이 설정되지 않았습니다. web/.env.local 확인",
        );
      }
      const res = await fetch(`${apiUrl}/api/portfolio`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
      });
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`HTTP ${res.status}: ${body}`);
      }
      return (await res.json()) as PortfolioReport;
    },
  });
}
