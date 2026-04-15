import type { Coverage } from "@/types/api";

/**
 * 커버리지 비율(가중평균에 실제 기여한 종목의 가치 비중) 배지.
 * - ≥ 0.9: 초록 (충분)
 * - ≥ 0.7: 노랑 (주의)
 * - < 0.7: 빨강 (해석 주의 — 대부분 종목이 집계에서 제외됨)
 */
export default function CoverageBadge({ coverage }: { coverage: Coverage }) {
  const total = coverage.included_value + coverage.excluded_value;
  const ratio = total > 0 ? coverage.included_value / total : 0;

  const color =
    ratio >= 0.9
      ? "text-green-700 bg-green-50 border-green-200"
      : ratio >= 0.7
        ? "text-amber-700 bg-amber-50 border-amber-200"
        : "text-red-700 bg-red-50 border-red-200";

  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-xs ${color}`}
      title={
        coverage.excluded_codes.length > 0
          ? `제외된 종목: ${coverage.excluded_codes.join(", ")}`
          : undefined
      }
    >
      커버리지 {(ratio * 100).toFixed(0)}%
    </span>
  );
}
