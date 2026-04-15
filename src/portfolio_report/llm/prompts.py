"""LLM 프롬프트 빌더 (순수 함수).

원칙:
- 제공된 수치 이외는 추정 금지 (할루시네이션 방지).
- 한국어로 응답.
- 참고용임을 명시.
"""

from __future__ import annotations

from portfolio_report.llm.base import TechnicalContext

_INDICATOR_LABELS = {
    "ichimoku": "일목균형표",
    "rsi": "RSI (14일)",
    "macd": "MACD (12/26/9)",
    "bb": "볼린저밴드 (20일 ±2σ)",
}


def build_technical_system_prompt() -> str:
    return (
        "당신은 한국 주식시장의 기술적 분석 애널리스트입니다. "
        "사용자가 제공한 수치만을 근거로 간결하고 정확한 해석을 한국어로 제공합니다. "
        "제공되지 않은 지표·뉴스·외부 사실을 추정하거나 언급하지 않으며, "
        "명시적으로 제공된 신호 및 수치를 중심으로 설명합니다. "
        "본 해석은 참고용이며 투자 자문이 아님을 마지막에 한 줄로 덧붙입니다."
    )


def build_technical_user_prompt(ctx: TechnicalContext) -> str:
    lines: list[str] = [
        f"## 종목: {ctx.name} ({ctx.code})",
        f"현재가: {_fmt_price(ctx.current_price)}",
        "",
        "## 기술적 지표 신호",
    ]
    if ctx.signals:
        for key, label in _INDICATOR_LABELS.items():
            data = ctx.signals.get(key)
            if not data:
                continue
            lines.append(f"### {label}")
            signal = data.get("signal")
            for k, v in data.items():
                if k == "signal":
                    continue
                lines.append(f"- {k}: {_fmt_value(v)}")
            if signal:
                lines.append(f"- **신호: {signal}**")
            lines.append("")
    else:
        lines.append("(제공된 지표 없음)")
        lines.append("")

    if ctx.price_tail:
        lines.append("## 최근 시세 (최근 N일)")
        lines.append("| 날짜 | 시가 | 고가 | 저가 | 종가 | 거래량 |")
        lines.append("|---|---|---|---|---|---|")
        for row in ctx.price_tail[-10:]:
            lines.append(
                "| {Date} | {Open} | {High} | {Low} | {Close} | {Volume} |".format(
                    Date=row.get("Date", ""),
                    Open=_fmt_value(row.get("Open")),
                    High=_fmt_value(row.get("High")),
                    Low=_fmt_value(row.get("Low")),
                    Close=_fmt_value(row.get("Close")),
                    Volume=_fmt_value(row.get("Volume")),
                )
            )
        lines.append("")

    lines.append(
        "## 요청"
        "\n위 수치만을 근거로 이 종목의 최근 기술적 흐름을 3~5문장으로 해석해 주세요. "
        "과매수/과매도, 추세, 주요 지지·저항 수준의 시사점을 포함하되, "
        "제공되지 않은 값(예: 목표주가, 뉴스, 재무지표)은 언급하지 않습니다."
    )
    return "\n".join(lines)


def _fmt_price(value: float | None) -> str:
    if value is None:
        return "N/A (가격 미확보)"
    return f"{value:,.0f}원"


def _fmt_value(value) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, (int,)):
        return f"{value:,}"
    if isinstance(value, float):
        # 수치 규모에 따라 자동 포맷 (1000 이상은 정수, 그 외 소수 2자리)
        if abs(value) >= 1000:
            return f"{value:,.0f}"
        return f"{value:.2f}"
    return str(value)
