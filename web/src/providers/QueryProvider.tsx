"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useState, type ReactNode } from "react";

/**
 * App Router 전역 TanStack Query Provider.
 *
 * `useState(() => new QueryClient(...))`로 생성 — 함수 리렌더 시 클라이언트가
 * 재생성되지 않도록 보장. 모듈 스코프에 두면 SSR에서 요청 간 상태가 공유된다.
 *
 * DevTools는 개발 환경에서만 렌더 → 프로덕션 번들에는 포함되지 않는다.
 */
export default function QueryProvider({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // 포트폴리오 OHLCV는 장중 5분, 장 마감 후에는 훨씬 길게 유효
            // 초기값은 넉넉히 잡고 6e 후반에 조정
            staleTime: 60_000,
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={client}>
      {children}
      {process.env.NODE_ENV === "development" && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
}
