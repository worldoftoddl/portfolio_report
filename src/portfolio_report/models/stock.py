from __future__ import annotations

from pydantic import BaseModel


class StockInfo(BaseModel):
    """종목의 시장/펀더멘털 스냅샷."""

    code: str
    name: str
    current_price: float | None = None
    per: float | None = None
    forward_per: float | None = None
    beta: float | None = None          # 네이버 52주 베타
    eps: float | None = None
    market_cap: float | None = None    # 선택: 리포트용
