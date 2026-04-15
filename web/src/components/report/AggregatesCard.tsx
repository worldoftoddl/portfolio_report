import CoverageBadge from "@/components/report/CoverageBadge";
import type { PortfolioAggregates } from "@/types/api";

function formatNumber(value: number | null): string {
  if (value === null || Number.isNaN(value)) return "—";
  return value.toFixed(2);
}

function Card({
  label,
  value,
  coverage,
}: {
  label: string;
  value: string;
  coverage: PortfolioAggregates["per_coverage"];
}) {
  return (
    <div className="rounded border border-gray-200 bg-white p-4">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
      <div className="mt-2">
        <CoverageBadge coverage={coverage} />
      </div>
    </div>
  );
}

export default function AggregatesCard({
  aggregates,
}: {
  aggregates: PortfolioAggregates;
}) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <Card
        label="가중 PER"
        value={formatNumber(aggregates.weighted_per)}
        coverage={aggregates.per_coverage}
      />
      <Card
        label="가중 추정 PER"
        value={formatNumber(aggregates.weighted_forward_per)}
        coverage={aggregates.forward_per_coverage}
      />
      <Card
        label="가중 베타"
        value={formatNumber(aggregates.weighted_beta)}
        coverage={aggregates.beta_coverage}
      />
    </div>
  );
}
