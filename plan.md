# Phase 6 d~f 구현 계획

이전 Phase 6a~6c (견고성 트랙)은 완료된 상태. 이 문서는 대규모 트랙인 6d (FastAPI 백엔드) / 6e (Next.js 프론트엔드) / 6f (LLM 스트리밍)의 설계 확정안을 보존한다.

## 완료된 Phase (참고)
- **6a** `cbe502f` — pytest-vcr 통합 테스트 (네이버 구조 변경 조기 감지)
- **6b** `19089c8` — LLM 응답 캐시 (종목+날짜+신호 해시 키)
- **6c** `a78c30f` — 펀더멘털 폴백 (pykrx PER/EPS + KS11 252일 회귀 베타)

---

## 확정된 전체 결정사항
- **시작 순서**: 6a → 6b → 6c → 6d → 6e → 6f
- **저장소 구조**: 모노레포, 루트에 `web/` 디렉터리 추가
- **배포**: 로컬 전용 (`docker-compose`로 백엔드+프론트 일괄 실행)
- **프론트엔드 프레임워크**: Next.js 14 App Router (사용자 선택)
- **차트 라이브러리**: TradingView Lightweight Charts (Apache 2.0)
- **상태 관리**: TanStack Query (서버 상태 중심)

---

## Phase 6d: FastAPI 백엔드 (3~4일)

### 목표
`PortfolioAnalyzer`를 REST API로 노출. CLI와 동일 코어 공유.

### 작업 단위

1. **의존성 추가** (`pyproject.toml`)
   - `fastapi>=0.115`, `uvicorn[standard]>=0.30`
   - `[web]` optional group으로 분리 → CLI 전용 사용자에게 부담 없음
   - 복잡도: 낮음

2. **요청/응답 스키마** (`src/portfolio_report/api/schemas.py` 신규)
   - 기존 pydantic 모델(`PortfolioReport`, `HoldingInput`) 재사용
   - `PortfolioAnalyzeRequest` 래퍼만 신규 (indicators/ohlcv_days/use_llm 포함)
   - 복잡도: 낮음

3. **앱 팩토리 + DI** (`src/portfolio_report/api/app.py` 신규)
   - `create_app() -> FastAPI` 팩토리 (테스트 격리)
   - `Depends(get_analyzer)`로 싱글톤 주입
   - CORS 미들웨어: `allow_origins=settings.cors_origins`
   - `Settings`에 `cors_origins: list[str]` 추가
   - 복잡도: 중간

4. **엔드포인트: 포트폴리오 분석** (`api/routes/portfolio.py`)
   - `POST /api/portfolio`
   - 요청: `PortfolioAnalyzeRequest`
   - 내부: `asyncio.to_thread(analyzer.analyze, ...)` — 기존 동기 코어 블로킹 방지
   - 복잡도: 중간

5. **엔드포인트: 종목별 차트/해석** (`api/routes/technical.py`)
   - `GET /api/stock/{code}/ohlcv?days=180` — OHLCV + 지표 시계열 JSON
   - `POST /api/stock/{code}/llm-explain` — TechnicalContext → LLM 해석 (비스트리밍)
   - 복잡도: 중간

6. **API 시리얼라이저** (`api/serializers.py` 신규) ⚠️ **설계 변경**
   - **`TechnicalAnalysis`에 `chart_series` 필드를 추가하지 않음** (도메인 모델 오염 방지)
   - API 응답 시점에 `to_tradingview_series(df, signals) -> dict` 변환
   - 포맷: `{ohlcv: [{time, open, high, low, close, volume}], indicators: {ichimoku:{tenkan,kijun,span_a,span_b}, rsi:[...], macd:{...}, bb:{upper,mid,lower}}}` (모두 `{time, value}` 배열)
   - 기존 `charts.py` (Plotly)는 무수정 → CLI/HTML 리포트 회귀 없음
   - 복잡도: 중간

7. **에러 핸들링** (`api/errors.py`)
   - 커스텀 예외 → HTTPException 매핑
   - `TickerNotFound → 404`, `NaverFetchError → 503`
   - 응답 스키마: `{error: code, message: str}`
   - 복잡도: 낮음

8. **세마포어/레이트리미터** (`api/middleware.py` 또는 DI)
   - `asyncio.Semaphore(5)`로 동시 네이버 호출 제한
   - 필요 시 `slowapi`로 요청 단위 rate limit
   - 복잡도: 중간

9. **테스트** (`tests/api/test_portfolio_route.py`, `test_technical_route.py`)
   - `TestClient` + 모킹된 `PortfolioAnalyzer`
   - 정상/400/404/503 케이스
   - 복잡도: 중간

10. **CLI 서브커맨드: serve** (`cli.py`)
    - `portfolio-report serve --host 0.0.0.0 --port 8000 --reload`
    - 복잡도: 낮음

### JSON 스키마 미리보기

**`POST /api/portfolio`**
```json
// Request
{
  "holdings": [
    {"name": "삼성전자", "code": null, "quantity": 10},
    {"name": null, "code": "000660", "quantity": 5}
  ],
  "indicators": ["ichimoku", "rsi", "macd", "bb"],
  "ohlcv_days": 180,
  "use_llm": true
}

// Response = PortfolioReport.model_dump(mode="json") + 시리얼라이저 변환
{
  "generated_at": "2026-04-15T15:30:00",
  "portfolio": { "holdings": [...] },
  "aggregates": {
    "weighted_per": 22.43,
    "weighted_forward_per": 6.00,
    "weighted_beta": 1.44,
    "per_coverage": {...},
    "forward_per_coverage": {...},
    "beta_coverage": {...},
    "total_market_value": 8475500
  },
  "per_stock_analyses": [
    {
      "code": "005930",
      "name": "삼성전자",
      "indicators": { "rsi": {...}, "macd": {...} },
      "chart_series": {     // API 시리얼라이저가 주입
        "ohlcv": [...],
        "indicators": {...}
      },
      "llm_explanation": "..."
    }
  ],
  "warnings": []
}
```

**`GET /api/stock/{code}/ohlcv`**
```json
{
  "code": "005930",
  "name": "삼성전자",
  "series": {
    "ohlcv": [{"time": "2026-01-02", "open": 72000, ...}],
    "ichimoku": {"tenkan": [...], ...},
    "bb": {"upper": [...], "mid": [...], "lower": [...]},
    "rsi": [...],
    "macd": {"macd": [...], "signal": [...], "hist": [...]}
  }
}
```

### 성공 기준
- `curl -X POST localhost:8000/api/portfolio -d '@sample.json'`으로 CLI와 동일 결과 반환
- LLM 포함 응답 시간 ≤ 15초

---

## Phase 6e: Next.js 프론트엔드 (6~8일 — 학습 포함)

### 학습 전제
TypeScript/React/Next.js App Router/TanStack Query/Lightweight Charts를 처음 접한다고 전제. 순수 구현 4~5일 + 학습 시간.

**착수 전 권장**: 종목 1개 하드코딩 → Lightweight Charts 단일 렌더링 미니 프로젝트 0.5~1일 선행 (5d 시작 전 학습용).

### 작업 단위

1. **프로젝트 부트스트랩** (모노레포 루트에 `web/`)
   ```bash
   npx create-next-app@latest web --ts --app --tailwind --eslint
   ```
   - 의존성: `@tanstack/react-query`, `lightweight-charts`, `zod`, `axios`, `react-hook-form`, `@hookform/resolvers`, `papaparse`, `react-dropzone`
   - 복잡도: 낮음

2. **API 클라이언트 + 타입** (`web/src/lib/api.ts`, `web/src/types/api.ts`)
   - 백엔드 스키마와 일치하는 TS 타입 수동 정의 (초기)
   - zod 런타임 검증
   - 추후 `openapi-typescript` 자동화 고려
   - 복잡도: 낮음

3. **페이지 구성** (`web/src/app/`)
   - `/` 입력 폼 (종목명/코드 + 수량, CSV 업로드)
   - `/report/[id]` 결과 대시보드 (집계/보유/경고)
   - `/report/[id]/stock/[code]` 종목 상세 (차트 + 지표 + LLM 해석)
   - 복잡도: 중간

4. **상태 관리** (`web/src/providers/QueryProvider.tsx`)
   - TanStack Query `QueryClientProvider` 루트 wrap
   - 분석 결과는 `sessionStorage` 캐시 (`id = hash(inputs)`) — 백엔드 무상태 유지
   - Redux/Zustand 불필요
   - 복잡도: 낮음

5. **TradingView 차트 컴포넌트** ⚠️ **복잡도 높음**
   - `web/src/components/charts/CandlestickChart.tsx`
   - `createChart` + `addCandlestickSeries` + `addLineSeries`
   - **서브플롯 한계**: Lightweight Charts는 하나의 차트에 서로 다른 스케일 서브플롯 기본 미지원 → 메인+RSI+MACD 3개 차트 스택 + 시간축 동기화 콜백
   - 복잡도: 높음

6. **입력 폼** (`web/src/components/forms/HoldingsForm.tsx`)
   - React Hook Form + zod resolver
   - `react-dropzone` CSV 드롭존 + `papaparse` 파싱
   - 복잡도: 중간

7. **결과 대시보드** (`web/src/components/report/`)
   - `AggregatesCard.tsx`: 집계 카드
   - `CoverageBadge.tsx`: 커버리지 뱃지 (`< 0.7` 빨강, `< 0.9` 노랑, 이상 초록)
   - `HoldingsTable.tsx`: 종목명 클릭 → 상세 페이지
   - 복잡도: 중간

8. **환경변수/설정** (`web/.env.example`, `web/next.config.js`)
   - `NEXT_PUBLIC_API_URL=http://localhost:8000`
   - 복잡도: 낮음

9. **Docker Compose** (루트 `docker-compose.yml`)
   - `backend`: `uvicorn` 8000
   - `frontend`: `next dev` 3000
   - `make dev` 한 줄로 실행
   - 복잡도: 중간

10. **E2E 테스트** (`web/e2e/` Playwright, 선택)
    - 포트폴리오 입력 → 결과 → 종목 상세 전체 플로우 1개
    - MSW로 백엔드 모킹 또는 실 백엔드
    - 복잡도: 중간

### 성공 기준
- 브라우저에서 3종목 입력 → 30초 이내 결과 + 차트 확인
- 모바일 반응형 기본 동작

---

## Phase 6f: LLM 스트리밍 (2일)

### 목표
LLM 해석을 토큰 단위로 스트리밍하여 체감 지연 단축. 6e 완료 후 UX 개선 차원.

### 작업 단위

1. **BaseLLMClient 확장** (`llm/base.py`)
   - `explain_technical_stream(ctx) -> Iterator[str]` (선택 메서드)
   - 기본 구현: `explain_technical` 결과를 한 번에 yield (Fallback)
   - 기존 인터페이스 파괴 금지
   - 복잡도: 낮음

2. **ClaudeClient 스트리밍 구현** (`llm/claude_client.py`)
   - anthropic SDK `messages.stream()` 사용
   - **캐시 상호작용** ⚠️ 핵심:
     - 스트리밍 중 텍스트 누적 → **완료 시점에만** `cache.set`
     - 중간 중단된 응답은 절대 캐시 금지
   - 복잡도: 중간

3. **FastAPI SSE 엔드포인트** (`api/routes/technical.py`)
   - `POST /api/stock/{code}/llm-explain/stream` — `StreamingResponse(media_type="text/event-stream")`
   - 형식:
     ```
     data: {"delta": "첫 "}\n\n
     data: {"delta": "토큰 "}\n\n
     data: {"done": true}\n\n
     ```
   - 복잡도: 중간

4. **프론트엔드 스트리밍 수신** (`web/src/hooks/useLLMStream.ts`)
   - `EventSource` 또는 `fetch` + `ReadableStream`
   - 점진적 텍스트 append
   - **캐시 히트/미스 분기** ⚠️:
     - 캐시 히트 시 백엔드는 한 번에 전체 반환 (스트리밍 아님)
     - 프론트에서 두 경로 구분 필요: 즉시 반환 vs 스트림
   - 연결 끊김 → 에러 토스트 + 재시도 버튼
   - 복잡도: 중간

5. **테스트** (`tests/api/test_llm_stream.py`, `web/e2e/llm_stream.spec.ts`)
   - 가짜 Claude 스트림 → 3개 청크 수신 검증
   - 캐시 히트 시 1회 응답, 미스 시 다중 청크 검증
   - 복잡도: 중간

### 성공 기준
- LLM 해석 첫 토큰이 2초 이내 화면에 표시
- 연결 끊김 시 에러 처리 명확
- 캐시 히트 시 스트리밍 없이 즉시 반환

---

## 리스크 요약

| 리스크 | 영향 | 완화 |
|--------|------|------|
| CORS 설정 오류 | 중 | dev `localhost:3000` 고정, 운영 환경변수 분리 |
| 두 서버 운영 부담 | 중 | `docker-compose` + `make dev` 한 줄 실행 |
| API 키 프론트 노출 | 치명 | 프론트 번들에 키 절대 포함 금지, LLM 호출은 반드시 백엔드 경유 |
| 네이버 동시 호출 부하 | 중 | FastAPI에 `asyncio.Semaphore(5)` + 선택적 `slowapi` |
| VCR 카세트 stale | 낮 | 주 1회 `./scripts/refresh_cassettes.sh` |
| 차트 서브플롯 복잡도 | 중 | 메인+RSI+MACD 3차트 스택 + 시간축 동기화 |
| 스트리밍 중 연결 끊김 | 중 | 완료 시점에만 캐시, 클라이언트 재연결 + 에러 UI |
| TypeScript/React 학습 시간 | 중 | 6e 착수 전 0.5~1일 미니 프로젝트 선행 |

---

## 시간 요약

| Phase | 시간 | 릴리스 가능성 |
|-------|------|-------------|
| 6d FastAPI 백엔드 | 3~4일 | 독립 (curl로 사용) |
| 6e Next.js 프론트 (학습 포함) | 6~8일 | 6d 필요 |
| 6f LLM 스트리밍 | 2일 | 6d+6e 필요 |
| **합계** | **11~14일** | |

---

## 착수 체크리스트 (6d 시작 전)

- [ ] `pyproject.toml`에 `[web]` optional group 정의
- [ ] `cors_origins` Settings 필드 추가
- [ ] `api/` 디렉토리 레이아웃 확정
- [ ] `TechnicalAnalysis` 도메인 모델 무수정 원칙 확인
- [ ] `to_tradingview_series` 시리얼라이저 계약 스펙 문서화

## 착수 체크리스트 (6e 시작 전)

- [ ] 학습용 미니 프로젝트로 TradingView 차트 렌더 경험
- [ ] 백엔드 `/api/stock/{code}/ohlcv`가 Lightweight Charts 포맷으로 응답하는지 확인
- [ ] `make dev`로 백+프론트 함께 실행되는지 확인
