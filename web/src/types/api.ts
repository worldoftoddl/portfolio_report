// FastAPI 응답 타입 미러. 6e 후반에 openapi-typescript 자동화로 교체 예정.

export interface OhlcvPoint {
  time: string; // "YYYY-MM-DD"
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface LinePoint {
  time: string;
  value: number;
}

export interface IndicatorSeries {
  rsi?: LinePoint[];
  macd?: {
    macd: LinePoint[];
    signal: LinePoint[];
    hist: LinePoint[];
  };
  bb?: {
    upper: LinePoint[];
    mid: LinePoint[];
    lower: LinePoint[];
  };
  ichimoku?: {
    tenkan: LinePoint[];
    kijun: LinePoint[];
    span_a: LinePoint[];
    span_b: LinePoint[];
  };
}

export interface TechnicalSeriesResponse {
  code: string;
  name: string;
  series: {
    ohlcv: OhlcvPoint[];
    indicators: IndicatorSeries;
  };
  // 지표 요청 시 마지막 행 기반 신호 요약 (LLM 요청에 재사용)
  signals: Record<string, Record<string, unknown>>;
}

// --- POST /api/stock/{code}/llm-explain ---

export interface LLMExplainRequest {
  name: string;
  current_price?: number | null;
  signals?: Record<string, Record<string, unknown>>;
  price_tail?: Array<Record<string, unknown>>;
}

export interface LLMExplainResponse {
  code: string;
  explanation: string;
}

// --- POST /api/portfolio ---

export interface HoldingInput {
  name?: string | null;
  code?: string | null;
  quantity: number;
}

export interface PortfolioAnalyzeRequest {
  holdings: HoldingInput[];
  indicators?: string[];
  ohlcv_days?: number;
  use_llm?: boolean;
}

export interface StockInfo {
  code: string;
  name: string;
  current_price: number | null;
  market_cap: number | null;
  per: number | null;
  forward_per: number | null;
  eps: number | null;
  beta: number | null;
}

export interface Holding {
  code: string;
  name: string;
  quantity: number;
  stock: StockInfo | null;
}

export interface Coverage {
  metric: string;
  included_value: number;
  excluded_value: number;
  excluded_codes: string[];
}

export interface PortfolioAggregates {
  weighted_per: number | null;
  weighted_forward_per: number | null;
  weighted_beta: number | null;
  per_coverage: Coverage;
  forward_per_coverage: Coverage;
  beta_coverage: Coverage;
  total_market_value: number;
}

export interface TechnicalAnalysis {
  code: string;
  name: string;
  indicators: Record<string, Record<string, unknown>>;
  chart_html: string | null;
  llm_explanation: string | null;
}

export interface PortfolioReport {
  generated_at: string;
  portfolio: { holdings: Holding[] };
  aggregates: PortfolioAggregates;
  per_stock_analyses: TechnicalAnalysis[];
  warnings: string[];
}
