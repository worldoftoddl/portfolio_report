from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from portfolio_report.models.stock import StockInfo


class HoldingInput(BaseModel):
    """사용자 입력 (파일 파싱 직후) — 해석 전 상태."""

    name: str | None = None
    code: str | None = None
    quantity: float = Field(..., gt=0)

    @model_validator(mode="after")
    def _require_name_or_code(self) -> HoldingInput:
        if not self.name and not self.code:
            raise ValueError("각 항목은 name 또는 code 중 하나 이상을 포함해야 합니다")
        return self


class Holding(BaseModel):
    """해석이 완료되어 종목코드와 메타가 확정된 보유 항목."""

    code: str
    name: str
    quantity: float
    stock: StockInfo | None = None

    @property
    def market_value(self) -> float | None:
        if self.stock is None or self.stock.current_price is None:
            return None
        return self.stock.current_price * self.quantity
