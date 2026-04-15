export default function WarningsPanel({ warnings }: { warnings: string[] }) {
  if (warnings.length === 0) return null;
  return (
    <div className="rounded border border-amber-300 bg-amber-50 p-3">
      <h3 className="mb-1 text-sm font-semibold text-amber-900">
        경고 ({warnings.length})
      </h3>
      <ul className="list-disc space-y-0.5 pl-5 text-xs text-amber-800">
        {warnings.map((w, i) => (
          <li key={i}>{w}</li>
        ))}
      </ul>
    </div>
  );
}
