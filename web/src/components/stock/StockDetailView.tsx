"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import ChartContainer from "@/components/ChartContainer";
import LLMExplanation from "@/components/stock/LLMExplanation";
import { useOhlcv } from "@/hooks/useOhlcv";
import { loadReport, type StoredReport } from "@/lib/reportStorage";
import type { Holding } from "@/types/api";

const INDICATORS = ["ichimoku", "bb", "rsi", "macd"];

interface Props {
  reportId: string;
  code: string;
}

/**
 * 종목 상세 — 차트(오버레이/서브플롯) + 메타(대시보드에서 유래) + LLM 해석.
 *
 * sessionStorage 미스(딥링크 진입) 시에도 동작해야 하므로
 * 차트/해석 둘 다 독립 API 호출로 데이터를 얻고, 메타는 있으면 사용한다.
 */
export default function StockDetailView({ reportId, code }: Props) {
  const [stored, setStored] = useState<StoredReport | null | undefined>(undefined);
  useEffect(() => setStored(loadReport(reportId)), [reportId]);

  const holding: Holding | undefined = useMemo(() => {
    if (!stored) return undefined;
    return stored.report.portfolio.holdings.find((h) => h.code === code);
  }, [stored, code]);

  const ohlcvQuery = useOhlcv(code, 180, INDICATORS);
  const seriesName = ohlcvQuery.data?.name ?? holding?.name ?? code;
  const currentPrice =
    ohlcvQuery.data?.series.ohlcv.at(-1)?.close ??
    holding?.stock?.current_price ??
    null;

  // LLM 요청 컨텍스트 — signals는 ohlcv 응답에서, 최근 10일 price_tail도 동일 응답에서.
  const llmRequest = useMemo(
    () => ({
      name: seriesName,
      current_price: currentPrice,
      signals: ohlcvQuery.data?.signals ?? {},
      price_tail:
        ohlcvQuery.data?.series.ohlcv
          .slice(-10)
          .map((p) => ({
            Date: p.time,
            Open: p.open,
            High: p.high,
            Low: p.low,
            Close: p.close,
            Volume: p.volume,
          })) ?? [],
    }),
    [seriesName, currentPrice, ohlcvQuery.data],
  );

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between">
        <Link
          href={`/report/${reportId}`}
          className="text-sm text-blue-700 hover:underline"
        >
          ← 대시보드로 돌아가기
        </Link>
        <span className="text-xs text-gray-500">
          {seriesName} ({code})
          {currentPrice !== null && (
            <>
              {" "}· 현재가 <strong>{currentPrice.toLocaleString()}</strong>
            </>
          )}
        </span>
      </div>

      <ChartContainer code={code} days={180} indicators={INDICATORS} />

      <LLMExplanation
        code={code}
        request={llmRequest}
        disabled={ohlcvQuery.isPending || ohlcvQuery.isError}
      />
    </div>
  );
}
