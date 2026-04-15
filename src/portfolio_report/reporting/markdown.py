"""마크다운 리포트 렌더링.

차트는 포함하지 않음 (HTML 리포트 전용). 대신 수치 표 + 신호 요약 + LLM 해석 텍스트.
"""

from __future__ import annotations

from portfolio_report.models.portfolio import (
    Coverage,
    PortfolioReport,
    TechnicalAnalysis,
)

_INDICATOR_LABELS = {
    "ichimoku": "일목균형표",
    "rsi": "RSI (14)",
    "macd": "MACD (12/26/9)",
    "bb": "볼린저밴드 (20±2σ)",
}


def render_markdown(report: PortfolioReport) -> str:
    parts: list[str] = []
    parts.append("# 📊 포트폴리오 분석 리포트")
    parts.append("")
    parts.append(f"- 생성일시: {report.generated_at:%Y-%m-%d %H:%M:%S}")
    parts.append(f"- 총 평가금액: **{_fmt(report.aggregates.total_market_value, '원')}**")
    parts.append("")

    if report.warnings:
        parts.append("## ⚠ 경고")
        for w in report.warnings:
            parts.append(f"- {w}")
        parts.append("")

    parts.extend(_render_aggregates(report))
    parts.extend(_render_holdings(report))

    if report.per_stock_analyses:
        parts.extend(_render_technical(report.per_stock_analyses))

    parts.append("---")
    parts.append(
        "> 본 리포트는 네이버 증권 비공식 엔드포인트 및 공개 데이터 기반이며, "
        "투자 자문이 아닌 참고용입니다."
    )
    return "\n".join(parts)


def _render_aggregates(report: PortfolioReport) -> list[str]:
    agg = report.aggregates
    lines = ["## 포트폴리오 집계", ""]
    lines.append("| 지표 | 값 | 커버리지 | 제외 종목 |")
    lines.append("|---|---|---|---|")
    lines.append(
        f"| 가중 PER | {_fmt(agg.weighted_per)} | "
        f"{_cov_percent(agg.per_coverage)} | "
        f"{_excluded(agg.per_coverage)} |"
    )
    lines.append(
        f"| 가중 추정 PER | {_fmt(agg.weighted_forward_per)} | "
        f"{_cov_percent(agg.forward_per_coverage)} | "
        f"{_excluded(agg.forward_per_coverage)} |"
    )
    lines.append(
        f"| 가중 베타 (52주) | {_fmt(agg.weighted_beta)} | "
        f"{_cov_percent(agg.beta_coverage)} | "
        f"{_excluded(agg.beta_coverage)} |"
    )
    lines.append("")
    return lines


def _render_holdings(report: PortfolioReport) -> list[str]:
    lines = ["## 보유 종목", ""]
    lines.append("| 종목코드 | 종목명 | 수량 | 현재가 | 평가금액 | 비중 | PER | 추정PER | 베타 |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    portfolio = report.portfolio
    for h in portfolio.holdings:
        s = h.stock
        weight = portfolio.weight_of(h)
        lines.append(
            "| {code} | {name} | {qty} | {price} | {mv} | {w} | {per} | {fpr} | {beta} |".format(
                code=h.code,
                name=h.name,
                qty=f"{h.quantity:g}",
                price=_fmt(s.current_price if s else None, "원"),
                mv=_fmt(h.market_value, "원"),
                w=f"{weight:.1%}" if h.market_value else "-",
                per=_fmt(s.per if s else None),
                fpr=_fmt(s.forward_per if s else None),
                beta=_fmt(s.beta if s else None),
            )
        )
    lines.append("")
    return lines


def _render_technical(analyses: list[TechnicalAnalysis]) -> list[str]:
    lines = ["## 종목별 기술적 분석", ""]
    for ta in analyses:
        lines.append(f"### {ta.code} {ta.name}")
        lines.append("")
        if ta.indicators:
            lines.append("| 지표 | 수치 | 신호 |")
            lines.append("|---|---|---|")
            for key, data in ta.indicators.items():
                label = _INDICATOR_LABELS.get(key, key.upper())
                values = ", ".join(
                    f"{k}={_fmt(v) if isinstance(v, (int, float)) else v}"
                    for k, v in data.items()
                    if k != "signal"
                )
                lines.append(f"| {label} | {values} | {data.get('signal', '-')} |")
            lines.append("")
        if ta.llm_explanation:
            lines.append("**해석:**")
            lines.append("")
            lines.append("> " + ta.llm_explanation.replace("\n", "\n> "))
            lines.append("")
    return lines


def _cov_percent(cov: Coverage) -> str:
    return f"{cov.ratio:.1%}"


def _excluded(cov: Coverage) -> str:
    return ", ".join(cov.excluded_codes) if cov.excluded_codes else "-"


def _fmt(value, suffix: str = "") -> str:
    if value is None:
        return "-"
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(f) >= 1000:
        return f"{f:,.0f}{suffix}"
    return f"{f:.2f}{suffix}"
