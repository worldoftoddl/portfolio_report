// FastAPI 응답 타입 미러. 6e 후반에 openapi-typescript 자동화로 교체 예정.

export interface OhlcvPoint {
  time: string; // "YYYY-MM-DD"
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TechnicalSeriesResponse {
  code: string;
  name: string;
  series: {
    ohlcv: OhlcvPoint[];
    indicators: Record<string, unknown>;
  };
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
