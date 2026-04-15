# portfolio-report

한국 주식 포트폴리오의 PER/추정PER/베타 및 기술적 분석 리포트를 생성하는 CLI.

## 기능

- 종목별/포트폴리오 **PER·추정PER·52주 베타** (평가금액 가중평균 + 커버리지)
- 기술적 분석: **일목균형표, RSI, MACD, 볼린저밴드** (조합 자유)
- **Claude API 기반 지표 해석** (BaseLLMClient 추상 → Gemini/OpenAI 확장 가능)
- 출력 3종: **콘솔(rich) · 마크다운(텍스트) · HTML(Plotly 차트 포함)**

## 데이터 소스

- 1순위: 네이버 증권 비공식 엔드포인트
  - `polling.finance.naver.com/api/realtime/domestic/stock/{code}` — 실시간 시세
  - `finance.naver.com/item/main.naver?code={code}` — PER/추정PER/EPS
  - `navercomp.wisereport.co.kr/v2/company/c1010001.aspx` — 52주 베타
- 폴백: `FinanceDataReader` (종목 마스터 + OHLCV), `pykrx`

## 설치

```bash
uv sync
cp .env.example .env
# .env에 ANTHROPIC_API_KEY=sk-ant-xxxxx 입력 (LLM 해석 사용 시)
```

## 포트폴리오 입력 형식

`examples/portfolio.yaml`:

```yaml
holdings:
  - name: 삼성전자        # 종목명 입력
    quantity: 10
  - code: "000660"        # 또는 종목코드 직접 입력
    quantity: 5
```

- 종목명 입력 시 우선주(삼성전자우 등)가 있으면 경고 출력
- 종목코드는 6자리 문자열 (앞 0 유지)

## 실행 예시

```bash
# 1) 콘솔 테이블 + 집계 (기본)
portfolio-report analyze -i examples/portfolio.yaml

# 2) 마크다운 리포트 (차트 없음, 텍스트 요약)
portfolio-report analyze -i examples/portfolio.yaml --format markdown -o report.md

# 3) HTML 리포트 (Plotly 차트 포함, 기술적 분석 시 자동 기본)
portfolio-report analyze -i examples/portfolio.yaml \
    --indicators ichimoku,rsi,macd,bb

# 4) 특정 지표만 + LLM 생략
portfolio-report analyze -i examples/portfolio.yaml \
    --indicators rsi,bb --no-llm

# 5) 특정 파일에 HTML 저장
portfolio-report analyze -i examples/portfolio.yaml \
    --indicators ichimoku --format html -o samsung.html
```

### 지표 선택 정책

- **오버레이** (가격 차트 위): `ichimoku`, `bb`
- **서브플롯** (독립 y축): `rsi`, `macd`
- 조합 자유 — 예: `--indicators rsi,bb` → 캔들+BB + 하단 RSI 패널

## 출력 정책

| 포맷 | 차트 | LLM 해석 | 용도 |
|------|------|---------|------|
| `console` | ❌ | 표시 생략 | 빠른 확인 |
| `markdown` | ❌ | 텍스트 | 공유/문서화 |
| `html` | ✅ Plotly | 텍스트 | 일반 리포트 |

## 프로젝트 구조

```
src/portfolio_report/
├── cli.py, config.py, portfolio_loader.py
├── models/     # Holding, Portfolio, StockInfo, Coverage
├── data/       # naver_client, naver_parser, price_client, ticker_resolver, cache
├── analysis/   # valuation(가중평균), technical(지표 4종), aggregator(오케스트)
├── llm/        # base(ABC), prompts, claude_client
└── reporting/  # console, markdown, html, charts(Plotly)

tests/
├── test_naver_parser.py    # 15 케이스 (100% 커버리지)
├── test_valuation.py       # 16 케이스 (100% 커버리지)
├── test_prompts.py         # 15 케이스 (96% 커버리지)
├── test_markdown.py        # 17 케이스 (97% 커버리지)
└── fixtures/naver/         # 실샘플 HTML/JSON
```

## 테스트

```bash
uv run pytest                 # 63 tests
uv run pytest --cov           # 커버리지 포함
```

critical path (네이버 파서 + 가중평균 + 프롬프트 + 마크다운)만 집중 테스트.

## 개발

```bash
make fmt        # ruff 자동 수정
make lint       # 린트 체크
make test       # pytest
```

## 로드맵

- ✅ Phase 1-5: CLI MVP (3종 출력 포맷)
- (선택) 웹 대시보드: FastAPI + Next.js + TradingView Lightweight Charts
- (선택) pytest-vcr로 네이버 응답 녹화
- (선택) LLM 스트리밍 응답
