import StockDetailView from "@/components/stock/StockDetailView";

export default async function StockDetailPage({
  params,
}: {
  params: Promise<{ id: string; code: string }>;
}) {
  const { id, code } = await params;
  return (
    <main className="mx-auto max-w-6xl p-6">
      <header className="mb-4">
        <h1 className="text-2xl font-bold">종목 상세</h1>
      </header>
      <StockDetailView reportId={id} code={code} />
    </main>
  );
}
