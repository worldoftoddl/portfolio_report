"use client";

import HoldingsForm from "@/components/forms/HoldingsForm";
import { usePortfolioAnalysis } from "@/hooks/usePortfolioAnalysis";

/**
 * 폼 + 결과 표시를 묶은 클라이언트 컨테이너.
 *
 * 6e-3 스코프: 결과를 `<pre>` JSON 뷰어에 덤프. 라우팅과 대시보드 카드는
 * 6e-4(결과 페이지), 6e-5(대시보드 컴포넌트)에서 도입.
 */
export default function AnalyzePanel() {
  const mutation = usePortfolioAnalysis();

  return (
    <div className="space-y-6">
      <HoldingsForm
        onSubmit={(req) => mutation.mutate(req)}
        isSubmitting={mutation.isPending}
      />

      {mutation.error && (
        <div className="rounded border border-red-300 bg-red-50 p-4 text-sm text-red-700">
          분석 실패: {mutation.error.message}
        </div>
      )}

      {mutation.data && (
        <section className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <MetricCard
              label="가중 PER"
              value={formatNumber(mutation.data.aggregates.weighted_per)}
              coverage={mutation.data.aggregates.per_coverage}
            />
            <MetricCard
              label="가중 추정 PER"
              value={formatNumber(
                mutation.data.aggregates.weighted_forward_per,
              )}
              coverage={mutation.data.aggregates.forward_per_coverage}
            />
            <MetricCard
              label="가중 베타"
              value={formatNumber(mutation.data.aggregates.weighted_beta)}
              coverage={mutation.data.aggregates.beta_coverage}
            />
          </div>

          {mutation.data.warnings.length > 0 && (
            <div className="rounded border border-amber-300 bg-amber-50 p-3">
              <h3 className="mb-1 text-sm font-semibold text-amber-900">
                경고 ({mutation.data.warnings.length})
              </h3>
              <ul className="list-disc pl-5 text-xs text-amber-800 space-y-0.5">
                {mutation.data.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          <details className="rounded border border-gray-200 bg-gray-50">
            <summary className="cursor-pointer px-3 py-2 text-sm text-gray-700">
              전체 응답 JSON (디버그)
            </summary>
            <pre className="overflow-auto p-3 text-xs text-gray-800">
              {JSON.stringify(mutation.data, null, 2)}
            </pre>
          </details>
        </section>
      )}
    </div>
  );
}

function formatNumber(value: number | null): string {
  if (value === null || Number.isNaN(value)) return "—";
  return value.toFixed(2);
}

function MetricCard({
  label,
  value,
  coverage,
}: {
  label: string;
  value: string;
  coverage: { included_value: number; excluded_value: number };
}) {
  const total = coverage.included_value + coverage.excluded_value;
  const ratio = total > 0 ? coverage.included_value / total : 0;
  const ratioColor =
    ratio >= 0.9
      ? "text-green-700"
      : ratio >= 0.7
        ? "text-amber-700"
        : "text-red-700";

  return (
    <div className="rounded border border-gray-200 bg-white p-4">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="mt-1 text-xl font-semibold">{value}</div>
      <div className={`mt-1 text-xs ${ratioColor}`}>
        커버리지 {(ratio * 100).toFixed(0)}%
      </div>
    </div>
  );
}
