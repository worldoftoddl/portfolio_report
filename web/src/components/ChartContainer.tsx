"use client";

import {
  CandlestickSeries,
  HistogramSeries,
  createChart,
  type IChartApi,
  type Time,
} from "lightweight-charts";
import { useEffect, useRef } from "react";

import { useOhlcv } from "@/hooks/useOhlcv";

/**
 * 삼성전자 캔들스틱 + 거래량 패널 차트.
 *
 * ## 학습 포인트
 *
 * 1. `'use client'`: `createChart`가 브라우저 canvas API를 쓰므로 서버 컴포넌트 불가.
 * 2. `useRef`로 마운트된 DOM div를 차트 컨테이너로 전달.
 * 3. `useEffect` 클린업 — `return () => chart.remove()`이 없으면 React Strict Mode
 *    (개발 기본 활성)에서 effect가 두 번 실행되어 차트 두 개가 겹쳐 렌더링된다.
 * 4. 데이터 페칭은 `useOhlcv`(TanStack Query)로 추출 — ChartContainer는 렌더링만 담당.
 */
export default function ChartContainer() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { data: response, error, isPending } = useOhlcv("005930", 180);
  const ohlcv = response?.series.ohlcv;

  useEffect(() => {
    if (!containerRef.current || !ohlcv || ohlcv.length === 0) return;

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
      ohlcv.map((p) => ({
        time: p.time as Time,
        open: p.open,
        high: p.high,
        low: p.low,
        close: p.close,
      })),
    );

    chart.addPane();
    const volume = chart.addSeries(
      HistogramSeries,
      {
        priceFormat: { type: "volume" },
        priceScaleId: "",
        color: "#94a3b8",
      },
      1,
    );
    volume.setData(
      ohlcv.map((p) => ({
        time: p.time as Time,
        value: p.volume,
        color: p.close >= p.open ? "#fecaca" : "#bfdbfe",
      })),
    );

    chart.timeScale().fitContent();

    return () => {
      chart.remove();
    };
  }, [ohlcv]);

  if (error) {
    return (
      <div className="rounded border border-red-300 bg-red-50 p-4 text-sm text-red-700">
        차트 데이터 로딩 실패: {error.message}
        <div className="mt-2 text-xs text-red-600">
          FastAPI 서버(localhost:8000)가 실행 중인지 확인하세요.
        </div>
      </div>
    );
  }

  if (isPending) {
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
