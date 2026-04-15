"use client";

import {
  CandlestickSeries,
  HistogramSeries,
  createChart,
  type IChartApi,
  type Time,
} from "lightweight-charts";
import { useEffect, useRef, useState } from "react";

import type { OhlcvPoint, TechnicalSeriesResponse } from "@/types/api";

/**
 * 삼성전자 캔들스틱 + 거래량 패널 차트.
 *
 * ## 학습 포인트
 *
 * 1. `'use client'`: `createChart`가 브라우저 canvas API를 쓰므로 서버 컴포넌트 불가.
 * 2. `useRef`로 마운트된 DOM div를 차트 컨테이너로 전달.
 * 3. `useEffect` 클린업 — `return () => chart.remove()`이 없으면 React Strict Mode
 *    (개발 기본 활성)에서 effect가 두 번 실행되어 차트 두 개가 겹쳐 렌더링된다.
 *    이건 React 버그가 아니라 Strict Mode가 클린업 누락을 드러내주는 장치.
 * 4. fetch는 별도 effect로 분리 — 데이터와 차트 생명주기가 다르기 때문.
 *    (6e에서 TanStack Query로 교체)
 */
export default function ChartContainer() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<OhlcvPoint[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 1) 데이터 페칭 — 브라우저가 cross-origin으로 FastAPI에 직접 호출.
  //    실패 시 백엔드 `cors_origins` 설정을 먼저 의심.
  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) {
      setError(
        "NEXT_PUBLIC_API_URL이 설정되지 않았습니다. web/.env.local을 확인하세요.",
      );
      return;
    }
    const ac = new AbortController();
    fetch(`${apiUrl}/api/stock/005930/ohlcv?days=180`, { signal: ac.signal })
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
        return (await r.json()) as TechnicalSeriesResponse;
      })
      .then((body) => setData(body.series.ohlcv))
      .catch((e: unknown) => {
        if (e instanceof Error && e.name !== "AbortError") setError(e.message);
      });
    return () => ac.abort();
  }, []);

  // 2) 차트 렌더 — 데이터가 도착하면 마운트.
  useEffect(() => {
    if (!containerRef.current || !data || data.length === 0) return;

    const chart: IChartApi = createChart(containerRef.current, {
      autoSize: true,
      layout: {
        background: { color: "#ffffff" },
        textColor: "#1f2937",
      },
      grid: {
        vertLines: { color: "#e5e7eb" },
        horzLines: { color: "#e5e7eb" },
      },
      rightPriceScale: { borderColor: "#d1d5db" },
      timeScale: { borderColor: "#d1d5db" },
    });

    const candle = chart.addSeries(CandlestickSeries, {
      upColor: "#dc2626",
      downColor: "#2563eb",
      borderUpColor: "#dc2626",
      borderDownColor: "#2563eb",
      wickUpColor: "#dc2626",
      wickDownColor: "#2563eb",
    });
    candle.setData(
      data.map((p) => ({
        time: p.time as Time,
        open: p.open,
        high: p.high,
        low: p.low,
        close: p.close,
      })),
    );

    // 거래량 전용 2번째 pane (v5 네이티브 지원)
    chart.addPane();
    const volume = chart.addSeries(
      HistogramSeries,
      {
        priceFormat: { type: "volume" },
        priceScaleId: "",
        color: "#94a3b8",
      },
      1, // paneIndex
    );
    volume.setData(
      data.map((p) => ({
        time: p.time as Time,
        value: p.volume,
        color: p.close >= p.open ? "#fecaca" : "#bfdbfe",
      })),
    );

    chart.timeScale().fitContent();

    // Strict Mode 클린업 — 이 return이 없으면 차트가 두 번 겹쳐 그려진다.
    return () => {
      chart.remove();
    };
  }, [data]);

  if (error) {
    return (
      <div className="rounded border border-red-300 bg-red-50 p-4 text-sm text-red-700">
        차트 데이터 로딩 실패: {error}
        <div className="mt-2 text-xs text-red-600">
          FastAPI 서버(localhost:8000)가 실행 중인지 확인하세요.
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex h-[500px] items-center justify-center text-gray-500">
        데이터 로딩 중…
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="h-[500px] w-full rounded border border-gray-200"
    />
  );
}
