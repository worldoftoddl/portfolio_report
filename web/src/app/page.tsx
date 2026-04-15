import ChartContainer from "@/components/ChartContainer";

// 서버 컴포넌트 (기본). Next 16 App Router.
// 학습용 미니 페이지 — 1종목 하드코딩, 차트는 클라이언트 컴포넌트로 분리.
export default function Home() {
  return (
    <main className="mx-auto max-w-6xl p-6">
      <header className="mb-4">
        <h1 className="text-2xl font-bold">삼성전자 (005930)</h1>
        <p className="text-sm text-gray-500">
          최근 180일 · 캔들스틱 + 거래량 · Lightweight Charts v5 학습 미니 프로젝트
        </p>
      </header>
      <ChartContainer />
      <footer className="mt-4 text-xs text-gray-400">
        데이터: FastAPI (<code>localhost:8000/api/stock/005930/ohlcv</code>)
        · next.config.ts의 rewrites로 <code>/api/*</code> 프록시
      </footer>
    </main>
  );
}
