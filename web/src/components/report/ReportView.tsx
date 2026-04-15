"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import AggregatesCard from "@/components/report/AggregatesCard";
import HoldingsTable from "@/components/report/HoldingsTable";
import WarningsPanel from "@/components/report/WarningsPanel";
import { loadReport, type StoredReport } from "@/lib/reportStorage";

/**
 * sessionStorage에서 리포트를 꺼내 렌더링. SSR 단계에선 storage 접근 불가이므로
 * useEffect로 hydrate 후 표시. 못 찾으면 폼으로 되돌아가는 안내.
 */
export default function ReportView({ id }: { id: string }) {
  const [stored, setStored] = useState<StoredReport | null | undefined>(undefined);

  useEffect(() => {
    setStored(loadReport(id));
  }, [id]);

  if (stored === undefined) {
    return <p className="text-sm text-gray-500">리포트 로딩 중…</p>;
  }

  if (stored === null) {
    return (
      <div className="rounded border border-gray-200 bg-gray-50 p-6 text-sm">
        <p className="text-gray-700">
          이 리포트를 찾을 수 없습니다. 결과는 브라우저 탭에만 저장되므로 새
          탭에서는 접근할 수 없습니다.
        </p>
        <Link
          href="/"
          className="mt-3 inline-block text-blue-700 hover:underline"
        >
          ← 폼으로 돌아가기
        </Link>
      </div>
    );
  }

  const { report } = stored;
  const savedAt = new Date(stored.savedAt).toLocaleString("ko-KR");

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between">
        <Link href="/" className="text-sm text-blue-700 hover:underline">
          ← 새 포트폴리오 분석
        </Link>
        <span className="text-xs text-gray-500">
          생성: {savedAt} · 종목 {report.portfolio.holdings.length}개
        </span>
      </div>

      <AggregatesCard aggregates={report.aggregates} />
      <WarningsPanel warnings={report.warnings} />
      <HoldingsTable reportId={id} holdings={report.portfolio.holdings} />
    </div>
  );
}
