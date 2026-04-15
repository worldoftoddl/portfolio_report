import AnalyzePanel from "@/components/AnalyzePanel";

// 서버 컴포넌트 — 정적 쉘 + 클라이언트 폼 패널 임베드.
// 라우팅(/report/[id])은 6e-4에서.
export default function Home() {
  return (
    <main className="mx-auto max-w-5xl p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-bold">포트폴리오 분석</h1>
        <p className="text-sm text-gray-500">
          보유 종목을 입력하고 [분석 시작]을 누르면 가중평균 PER·베타와 경고를
          확인할 수 있습니다.
        </p>
      </header>
      <AnalyzePanel />
    </main>
  );
}
