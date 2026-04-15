import ReportView from "@/components/report/ReportView";

// Next 15+ 부터 params는 Promise — async 서버 컴포넌트로 받는다.
export default async function ReportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <main className="mx-auto max-w-5xl p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-bold">포트폴리오 리포트</h1>
        <p className="text-xs text-gray-500 font-mono">id: {id}</p>
      </header>
      <ReportView id={id} />
    </main>
  );
}
