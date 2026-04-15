"use client";

import { useQuery } from "@tanstack/react-query";

import type { TechnicalSeriesResponse } from "@/types/api";

/**
 * FastAPI `/api/stock/{code}/ohlcv`를 호출하는 Query 훅.
 *
 * - queryKey: `['ohlcv', code, days, indicators]` (지표별 키 분리)
 * - signal: TanStack Query가 주입 → 훅 언마운트 시 자동 abort
 * - indicators: 각 항목이 `indicators` query param으로 반복되어 전송됨
 */
export function useOhlcv(
  code: string,
  days: number = 180,
  indicators: string[] = [],
) {
  return useQuery({
    queryKey: ["ohlcv", code, days, indicators] as const,
    queryFn: async ({ signal }) => {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      if (!apiUrl) {
        throw new Error(
          "NEXT_PUBLIC_API_URL이 설정되지 않았습니다. web/.env.local 확인",
        );
      }
      const params = new URLSearchParams();
      params.set("days", String(days));
      for (const ind of indicators) params.append("indicators", ind);

      const res = await fetch(
        `${apiUrl}/api/stock/${code}/ohlcv?${params.toString()}`,
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
