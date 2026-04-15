"use client";

import { useQuery } from "@tanstack/react-query";

import type { TechnicalSeriesResponse } from "@/types/api";

/**
 * FastAPI `/api/stock/{code}/ohlcv`를 호출하는 Query 훅.
 *
 * - queryKey: `['ohlcv', code, days]` — DevTools에서 식별자로 보인다
 * - signal: TanStack Query가 주입 → 훅 언마운트 시 자동 abort
 * - staleTime: Provider 기본값(60초) 상속. 종목 상세 페이지 간 빠른 이동 시 재호출 방지
 */
export function useOhlcv(code: string, days: number = 180) {
  return useQuery({
    queryKey: ["ohlcv", code, days] as const,
    queryFn: async ({ signal }) => {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      if (!apiUrl) {
        throw new Error(
          "NEXT_PUBLIC_API_URL이 설정되지 않았습니다. web/.env.local 확인",
        );
      }
      const res = await fetch(
        `${apiUrl}/api/stock/${code}/ohlcv?days=${days}`,
        { signal },
      );
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`HTTP ${res.status}: ${body}`);
      }
      return (await res.json()) as TechnicalSeriesResponse;
    },
  });
}
