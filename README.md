# portfolio-report

한국 주식 포트폴리오의 PER/추정PER/베타 및 기술적 분석 리포트를 생성하는 CLI 도구.

## 기능
- 종목별/포트폴리오 PER, 추정PER (평가금액 가중평균)
- 포트폴리오 베타 (네이버 52주 베타 가중평균)
- 기술적 분석: 일목균형표, RSI, MACD, 볼린저밴드
- Claude API 기반 지표 해석
- 출력: 콘솔(rich), 마크다운, Plotly HTML

## 데이터 소스
- 1순위: 네이버 증권 비공식 엔드포인트
- 폴백: pykrx, FinanceDataReader

## 설치
```bash
uv sync
cp .env.example .env   # ANTHROPIC_API_KEY 입력
```

## 실행
```bash
# 기본 분석
portfolio-report analyze -i examples/portfolio.yaml

# 기술적 분석 포함 (HTML 리포트 자동 생성)
portfolio-report analyze -i examples/portfolio.yaml --indicators ichimoku,rsi,macd,bb

# LLM 해석 생략
portfolio-report analyze -i examples/portfolio.yaml --no-llm
```

## 포트폴리오 입력 형식
`examples/portfolio.yaml`:
```yaml
holdings:
  - name: 삼성전자
    quantity: 10
  - code: "000660"       # 종목코드 직접 지정도 가능
    quantity: 5
```
