# portfolio-report

한국 주식 포트폴리오의 **PER·추정PER·52주 베타**와 **기술적 분석**을 산출하고,
Claude API로 해석까지 붙여주는 CLI + 웹 대시보드.

## 기능

- **포트폴리오 집계**: 평가금액 가중 PER·추정PER·베타 + 커버리지 비율
- **기술적 분석**: 일목균형표, RSI, MACD, 볼린저밴드 (조합 자유)
- **LLM 해석**: Claude 4 Sonnet 기본. `BaseLLMClient` ABC로 제공자 교체 가능
- **3가지 인터페이스**
  - **CLI**: 콘솔 테이블 · Markdown · Plotly HTML 리포트
  - **FastAPI 백엔드**: 프런트/외부 클라이언트가 쓰는 REST + SSE API
  - **Next.js 웹**: TradingView Lightweight Charts 기반 대시보드 + 종목 상세
- **LLM 스트리밍 (SSE)**: 첫 토큰 ≤ 2초, 캐시 히트 시 즉시 전체 반환,
  연결 끊김 시 부분 응답 캐시 금지 (정합성 보장)
- **이중 캐시**: 가격/펀더멘털 diskcache(장중 5분/장마감 12시간/펀더멘털 1일) +
  LLM 응답 캐시(종목+KST 날짜+signals 해시 키)
- **견고성**: 네이버 실패 시 pykrx PER/EPS + FDR 기반 KS11 252일 회귀 베타로 폴백
- **VCR 통합 테스트**로 네이버 HTML 구조 변경 조기 감지

## 스크린샷

아래 경로에 직접 캡처를 저장하면 이 섹션에 렌더링됩니다.

| 대시보드 | 종목 상세 |
|---|---|
| ![dashboard](docs/screenshots/dashboard.png) | ![stock-detail](docs/screenshots/stock-detail.png) |

파일명 규칙: `docs/screenshots/{dashboard,stock-detail}.png`

## 데이터 소스

| 용도 | 1순위 | 폴백 |
|---|---|---|
| 실시간 시세 | 네이버 `polling.finance.naver.com/api/realtime/domestic/stock/{code}` | FDR OHLCV 마지막 종가 |
| PER/추정PER/EPS | 네이버 `finance.naver.com/item/main.naver?code={code}` | pykrx `get_market_fundamental` |
| 52주 베타 | 네이버 `navercomp.wisereport.co.kr/v2/company/c1010001.aspx` | FDR 기반 KS11 252일 회귀 |
| 종목 마스터 | FDR `StockListing("KRX")` | pykrx `get_market_ticker_list` |

코스닥 종목을 KS11 벤치마크로 회귀하는 경우 벤치마크 불일치 경고를 리포트에 포함.

## 빠른 시작

```bash
# 1) 저장소 클론 후 환경 파일
cp .env.example .env
# ANTHROPIC_API_KEY=sk-ant-xxxxx 를 .env에 기입

# 2) 파이썬 의존성 (CLI + 웹 API)
uv sync --extra web

# 3) 프런트 의존성
cd web && npm install && cd ..

# 4) 백엔드 + 프런트 동시 실행
make dev-local     # Docker 없이 로컬 프로세스 (Ctrl-C로 일괄 종료)
# 또는
make dev           # docker compose up --build (Docker Desktop WSL 통합 필요)
```

브라우저: `http://localhost:3000`

### `make` 타깃 전체

| 타깃 | 설명 |
|---|---|
| `make dev` | docker compose로 backend(8000) + frontend(3000) 동시 실행 |
| `make dev-local` | Docker 없이 로컬 프로세스로 동시 실행 |
| `make dev-backend` / `make dev-frontend` | 단독 실행 |
| `make test` / `make test-cov` | pytest (+ 커버리지) |
| `make lint` / `make fmt` | ruff |
| `make run` | CLI로 `examples/portfolio.yaml` 분석 |
| `make stop` | `docker compose down` |

## CLI 사용

### 포트폴리오 입력 형식 (`examples/portfolio.yaml`)

```yaml
holdings:
  - name: 삼성전자        # 종목명 입력
    quantity: 10
  - code: "000660"        # 또는 종목코드 직접 입력
    quantity: 5
```

- 종목명 입력 시 우선주(삼성전자우 등)가 있으면 경고 출력
- 종목코드는 6자리 문자열 (앞 0 유지)

### 실행 예시

```bash
# 1) 콘솔 테이블 + 집계 (기본)
portfolio-report analyze -i examples/portfolio.yaml

# 2) HTML 리포트 (Plotly 차트 + LLM 해석)
portfolio-report analyze -i examples/portfolio.yaml \
    --indicators ichimoku,rsi,macd,bb

# 3) 마크다운 (차트 없음, 텍스트 요약)
portfolio-report analyze -i examples/portfolio.yaml \
    --format markdown -o report.md

# 4) LLM 캐시 우회 (프롬프트 튜닝 시)
portfolio-report analyze -i examples/portfolio.yaml \
    --indicators rsi --no-llm-cache

# 5) API 서버 단독 실행
portfolio-report serve --host 127.0.0.1 --port 8000 --reload
```

#### 지표 선택 정책

- **오버레이** (가격 차트 위): `ichimoku`, `bb`
- **서브플롯** (독립 y축): `rsi`, `macd`
- 조합 자유 — 예: `--indicators rsi,bb` → 캔들+BB + 하단 RSI 패널

#### 출력 정책

| 포맷 | 차트 | LLM 해석 | 용도 |
|------|------|---------|------|
| `console` | ❌ | 표시 생략 | 빠른 확인 |
| `markdown` | ❌ | 텍스트 | 공유/문서화 |
| `html` | ✅ Plotly | 텍스트 | 일반 리포트 |

## 웹 대시보드

### 플로우

1. `/` 입력 폼 — 종목명(또는 코드) + 수량 행 추가/삭제, zod 검증
2. 제출 → `POST /api/portfolio` → `sessionStorage`에 결과 저장 후 `/report/{hash}`로 이동
3. 대시보드에서 가중 PER·추정PER·베타 + 커버리지 색상 배지 + 보유 종목 테이블
4. 종목명 클릭 → `/report/{hash}/stock/{code}` 상세
5. 상세 페이지에서 **캔들 + 일목/볼린저 오버레이 + RSI/MACD 서브플롯** (TradingView Lightweight Charts v5)
6. `AI 해석 요청` 버튼 → SSE로 토큰 단위 스트리밍 → 캐시 저장
7. 동일 요청 재클릭 시 캐시 히트 배지 + 즉시 전체 표시

### API 엔드포인트

| 메서드 + 경로 | 설명 |
|---|---|
| `POST /api/portfolio` | 포트폴리오 분석 → PortfolioReport |
| `GET /api/stock/{code}/ohlcv?days=&indicators=` | OHLCV + 지표 시리즈 (Lightweight Charts 포맷) + signals |
| `POST /api/stock/{code}/llm-explain` | 비스트리밍 LLM 해석 |
| `POST /api/stock/{code}/llm-explain/stream` | **SSE 스트리밍** LLM 해석 |

**SSE 이벤트 프로토콜** (`text/event-stream`):

```
data: {"type":"meta","cached":true,"text":"전체 해석..."}   ← 캐시 히트 1이벤트
data: {"type":"done"}

# or

data: {"type":"meta","cached":false}
data: {"type":"delta","text":"첫 "}
data: {"type":"delta","text":"토큰 "}
...
data: {"type":"done"}

# 실패 시
data: {"type":"error","message":"..."}
```

네이버/FDR 외부 호출 경로(`POST /api/portfolio`, `GET .../ohlcv`)는
`asyncio.Semaphore(settings.api_concurrency_limit)`로 동시성 제한.
Claude API 경로(LLM 엔드포인트 2종)는 **의도적으로 제외** — 네이버 스로틀과 무관.

## 프로젝트 구조

```
src/portfolio_report/
├── cli.py, config.py, portfolio_loader.py, __main__.py
├── models/        # Holding, Portfolio, StockInfo, Coverage, PortfolioReport
├── data/          # naver_client/parser, price_client, ticker_resolver,
│                  #   fundamental_fallback (pykrx+FDR 베타), cache
├── analysis/      # valuation(가중평균), technical(지표 4종), aggregator(오케스트)
├── llm/           # base(ABC), prompts, claude_client(동기+async), cache(키 해시)
├── reporting/     # console, markdown, html, charts(Plotly)
└── api/           # FastAPI: app(팩토리+lifespan), deps, schemas, errors,
                   #          serializers(to_tradingview_series), routes/

web/src/
├── app/                         # Next 16 App Router
│   ├── page.tsx                 # 입력 폼 쉘
│   └── report/[id]/
│       ├── page.tsx             # 대시보드
│       └── stock/[code]/page.tsx   # 상세
├── components/
│   ├── AnalyzePanel.tsx         # 폼 + mutation + router.push
│   ├── forms/HoldingsForm.tsx   # RHF + zod
│   ├── report/{Aggregates,Coverage,Holdings,Warnings}...
│   ├── stock/StockDetailView.tsx, LLMExplanation.tsx
│   └── ChartContainer.tsx       # TradingView Lightweight Charts v5
├── hooks/                       # useOhlcv, usePortfolioAnalysis, useLLMStream
├── lib/                         # schema(zod), reportStorage(sessionStorage+djb2)
├── types/api.ts                 # 백엔드 응답 미러
└── providers/QueryProvider.tsx  # TanStack Query v5

tests/
├── test_naver_parser.py, test_valuation.py, test_prompts.py, test_markdown.py
├── test_aggregator_fallback.py, test_fundamental_fallback.py
├── test_llm_cache.py, test_claude_cache.py, test_claude_stream.py
├── api/test_{app_smoke,portfolio_route,technical_route,
│            llm_stream_route,serializers,semaphore,cli_serve}.py
├── data/test_naver_client_vcr.py, cassettes/
└── fixtures/naver/              # 네이버 실샘플 HTML/JSON
```

## 테스트

```bash
make test                 # 전체 (현재 149 passed)
make test-cov             # 커버리지 포함
```

critical path (네이버 파서 · 가중평균 · 프롬프트 · 마크다운 · 베타 계산 ·
LLM 캐시 · 시리얼라이저) 100% 커버 + API 라우트/세마포어/스트리밍 통합 테스트.

### VCR (네이버 구조 변경 조기 감지)

```bash
# 기본: 카세트 재생만 (네트워크 0, CI 기본)
uv run pytest tests/data/test_naver_client_vcr.py

# 갱신 (네이버 HTML 변경 시)
./scripts/refresh_cassettes.sh
```

카세트 크기 관리를 위해 삼성전자(005930) 1종목만 녹화.
민감 헤더(Cookie/Auth/UA)는 REDACTED로 필터링.

## 아키텍처 메모

- **도메인 모델 무수정 원칙**: `TechnicalAnalysis` 등 pydantic 모델에
  API 전용 필드(`chart_series` 등)를 추가하지 않는다. 변환은
  `api/serializers.to_tradingview_series`가 전담.
- **`lifespan` 싱글톤**: `NaverClient`/`PortfolioAnalyzer`/`ClaudeClient`를
  앱 시작 시 한 번만 생성해 `app.state`에 보관. httpx 커넥션 풀 재사용.
- **LLM 캐시 키 공유**: 스트리밍/비스트리밍 엔드포인트가 같은
  `llm:{model}:{code}:{YYYY-MM-DD KST}:{signals_hash}` 키로 저장소 공유.
- **캐시 안전성**: 스트리밍 중간 연결 끊김 시 부분 누적 텍스트는 `cache.set`
  호출 전에 종료되어 저장되지 않는다 (6f 핵심 안전장치).

## 로드맵

- ✅ Phase 1–5: CLI MVP (3종 포맷)
- ✅ Phase 6a: pytest-vcr
- ✅ Phase 6b: LLM 응답 캐시
- ✅ Phase 6c: 펀더멘털 폴백 (pykrx + FDR 베타)
- ✅ Phase 6d: FastAPI 백엔드 + 세마포어
- ✅ Phase 6e: Next.js 대시보드 (입력 폼 → 대시보드 → 종목 상세)
- ✅ Phase 6e-7: Docker Compose + Makefile
- ✅ Phase 6f: LLM SSE 스트리밍
- ◻︎ CSV 업로드 (HoldingsForm 확장)
- ◻︎ Playwright E2E (핵심 플로우 1개)
- ◻︎ openapi-typescript 자동화
