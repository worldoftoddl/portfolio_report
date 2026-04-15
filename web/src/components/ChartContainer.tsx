"use client";

import {
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  LineStyle,
  createChart,
  type IChartApi,
  type Time,
} from "lightweight-charts";
import { useEffect, useRef } from "react";

import { useOhlcv } from "@/hooks/useOhlcv";
import type { IndicatorSeries, LinePoint } from "@/types/api";

interface ChartContainerProps {
  code: string;
  days?: number;
  indicators?: string[];
}

const DEFAULT_INDICATORS = ["ichimoku", "bb", "rsi", "macd"];

/**
 * 종목 차트 — 캔들스틱 + 거래량 + 지표 오버레이/서브플롯.
 *
 * Pane 배치:
 *   0 = 메인 (캔들 + ichimoku + bb 오버레이)
 *   1 = 거래량 히스토그램
 *   2 = RSI (70/30 기준선)
 *   3 = MACD (macd line + signal + histogram)
 */
export default function ChartContainer({
  code,
  days = 180,
  indicators = DEFAULT_INDICATORS,
}: ChartContainerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { data: response, error, isPending } = useOhlcv(code, days, indicators);

  useEffect(() => {
    if (!containerRef.current || !response) return;
    const ohlcv = response.series.ohlcv;
    if (ohlcv.length === 0) return;

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

    // --- 메인 pane: 캔들 ---
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

    // 메인 pane 오버레이: ichimoku, bb
    const ind: IndicatorSeries = response.series.indicators ?? {};
    if (ind.ichimoku) {
      addLine(chart, ind.ichimoku.tenkan, 0, { color: "#ea580c", lineWidth: 1 });
      addLine(chart, ind.ichimoku.kijun, 0, { color: "#0ea5e9", lineWidth: 1 });
      addLine(chart, ind.ichimoku.span_a, 0, {
        color: "#86efac",
        lineWidth: 1,
        lineStyle: LineStyle.Dotted,
      });
      addLine(chart, ind.ichimoku.span_b, 0, {
        color: "#fca5a5",
        lineWidth: 1,
        lineStyle: LineStyle.Dotted,
      });
    }
    if (ind.bb) {
      addLine(chart, ind.bb.upper, 0, {
        color: "#9ca3af",
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
      });
      addLine(chart, ind.bb.mid, 0, { color: "#6b7280", lineWidth: 1 });
      addLine(chart, ind.bb.lower, 0, {
        color: "#9ca3af",
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
      });
    }

    // --- 거래량 pane (1) ---
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

    // --- RSI pane (2) ---
    if (ind.rsi) {
      chart.addPane();
      const rsi = chart.addSeries(
        LineSeries,
        { color: "#7c3aed", lineWidth: 1, priceScaleId: "right" },
        2,
      );
      rsi.setData(toLineData(ind.rsi));
      rsi.createPriceLine({
        price: 70,
        color: "#d1d5db",
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: "",
        lineWidth: 1,
      });
      rsi.createPriceLine({
        price: 30,
        color: "#d1d5db",
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: "",
        lineWidth: 1,
      });
    }

    // --- MACD pane (3) ---
    if (ind.macd) {
      chart.addPane();
      const macdLine = chart.addSeries(
        LineSeries,
        { color: "#2563eb", lineWidth: 1 },
        3,
      );
      macdLine.setData(toLineData(ind.macd.macd));
      const signalLine = chart.addSeries(
        LineSeries,
        { color: "#dc2626", lineWidth: 1 },
        3,
      );
      signalLine.setData(toLineData(ind.macd.signal));
      const hist = chart.addSeries(
        HistogramSeries,
        { color: "#94a3b8", priceScaleId: "" },
        3,
      );
      hist.setData(
        ind.macd.hist.map((p) => ({
          time: p.time as Time,
          value: p.value,
          color: p.value >= 0 ? "#86efac" : "#fca5a5",
        })),
      );
    }

    chart.timeScale().fitContent();

    return () => {
      chart.remove();
    };
  }, [response]);

  if (error) {
    return (
      <div className="rounded border border-red-300 bg-red-50 p-4 text-sm text-red-700">
        차트 데이터 로딩 실패: {error.message}
      </div>
    );
  }

  if (isPending) {
    return (
      <div className="flex h-[600px] items-center justify-center text-gray-500">
        차트 데이터 로딩 중…
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="h-[600px] w-full rounded border border-gray-200"
    />
  );
}

function toLineData(points: LinePoint[]) {
  return points.map((p) => ({ time: p.time as Time, value: p.value }));
}

function addLine(
  chart: IChartApi,
  points: LinePoint[],
  paneIndex: number,
  options: Parameters<IChartApi["addSeries"]>[1],
) {
  const series = chart.addSeries(LineSeries, options, paneIndex);
  series.setData(toLineData(points));
  return series;
}
