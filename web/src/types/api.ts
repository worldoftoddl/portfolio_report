// FastAPI `to_tradingview_series` 응답 타입 미러.
// 6e에서 zod 런타임 검증 + openapi-typescript 자동화로 교체 예정.

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
