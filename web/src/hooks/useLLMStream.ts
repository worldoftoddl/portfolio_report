"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { LLMExplainRequest } from "@/types/api";

/**
 * SSE 스트리밍 수신 훅.
 *
 * - fetch + ReadableStream (EventSource는 POST 미지원)
 * - 이벤트 프로토콜: `{type: 'meta'|'delta'|'done'|'error'}`
 * - 캐시 히트(`meta.cached=true`) 시 `meta.text`로 즉시 전체 텍스트 표시
 * - 언마운트·재호출 시 AbortController로 이전 스트림 취소
 */
export function useLLMStream(code: string) {
  const [text, setText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isCached, setIsCached] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    setText("");
    setIsCached(false);
    setError(null);
  }, []);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
  }, []);

  const start = useCallback(
    async (req: LLMExplainRequest) => {
      abortRef.current?.abort();
      const ac = new AbortController();
      abortRef.current = ac;
      reset();
      setIsStreaming(true);

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL;
        if (!apiUrl) throw new Error("NEXT_PUBLIC_API_URL 미설정");

        const res = await fetch(
          `${apiUrl}/api/stock/${code}/llm-explain/stream`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(req),
            signal: ac.signal,
          },
        );
        if (!res.ok) {
          const body = await res.text();
          throw new Error(`HTTP ${res.status}: ${body}`);
        }
        if (!res.body) throw new Error("응답 본문이 비어 있습니다.");

        const reader = res.body
          .pipeThrough(new TextDecoderStream())
          .getReader();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += value;

          // SSE 이벤트는 `\n\n`으로 구분
          let idx: number;
          while ((idx = buffer.indexOf("\n\n")) !== -1) {
            const block = buffer.slice(0, idx);
            buffer = buffer.slice(idx + 2);
            const dataLine = block
              .split("\n")
              .find((l) => l.startsWith("data: "));
            if (!dataLine) continue;
            const ev = JSON.parse(dataLine.slice(6));
            handleEvent(ev);
          }
        }
      } catch (e: unknown) {
        if (e instanceof DOMException && e.name === "AbortError") {
          // 사용자/언마운트 취소 — 정상 종료
          return;
        }
        setError(e instanceof Error ? e : new Error(String(e)));
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }

      function handleEvent(ev: {
        type: string;
        cached?: boolean;
        text?: string;
        message?: string;
      }) {
        if (ev.type === "meta") {
          if (ev.cached) {
            setIsCached(true);
            if (ev.text) setText(ev.text);
          } else {
            setIsCached(false);
          }
        } else if (ev.type === "delta") {
          if (ev.text) setText((prev) => prev + ev.text);
        } else if (ev.type === "error") {
          throw new Error(ev.message ?? "스트리밍 오류");
        }
        // 'done'은 단순 종결 신호 — reader.read()가 자연스럽게 done=true 반환
      }
    },
    [code, reset],
  );

  // 언마운트 시 진행 중 스트림 정리
  useEffect(
    () => () => {
      abortRef.current?.abort();
    },
    [],
  );

  return { text, isStreaming, isCached, error, start, cancel, reset };
}
