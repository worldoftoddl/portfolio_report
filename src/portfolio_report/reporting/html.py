"""HTML 리포트 렌더링. 포트폴리오 요약 + 종목별 Plotly 차트."""

from __future__ import annotations

from html import escape

from portfolio_report.models.portfolio import Coverage, PortfolioReport


_CSS = """
<style>
  body { font-family: -apple-system, "Malgun Gothic", sans-serif; margin: 24px; color: #222; background: #fafafa; }
  h1 { border-bottom: 2px solid #2c3e50; padding-bottom: 6px; }
  h2 { margin-top: 32px; color: #2c3e50; }
  h3 { margin-top: 20px; color: #34495e; }
  table { border-collapse: collapse; margin: 8px 0; font-size: 14px; }
  th, td { border: 1px solid #ddd; padding: 6px 12px; text-align: right; }
  th { background: #ecf0f1; }
  td:first-child, th:first-child { text-align: left; }
  .coverage { color: #7f8c8d; font-size: 13px; }
  .warning { background: #fff8dc; padding: 10px 14px; border-left: 4px solid #f39c12;
             margin: 8px 0; border-radius: 4px; }
  .aggregates { background: #ecf0f1; padding: 12px 16px; border-radius: 6px;
                display: inline-block; font-size: 15px; }
  .signal { color: #16a085; font-weight: 600; }
  .signal-neg { color: #c0392b; font-weight: 600; }
  .disclaimer { font-size: 12px; color: #95a5a6; margin-top: 40px; }
</style>
"""


def render_html(report: PortfolioReport) -> str:
    parts = [
        "<!DOCTYPE html>",
        '<html lang="ko"><head>',
        '<meta charset="UTF-8">',
        f"<title>포트폴리오 리포트 {report.generated_at:%Y-%m-%d %H:%M}</title>",
        _CSS,
        "</head><body>",
        f"<h1>📊 포트폴리오 분석 리포트</h1>",
        f"<p>생성일시: {report.generated_at:%Y-%m-%d %H:%M:%S}</p>",
        _render_warnings(report),
        _render_aggregates(report),
        _render_holdings_table(report),
        _render_per_stock(report),
        '<div class="disclaimer">'
        "※ 본 리포트는 네이버 증권 비공식 엔드포인트 및 공개 데이터를 기반으로 하며, "
        "투자 자문이 아닙니다. LLM 해석이 포함된 경우 그 내용은 참고용입니다."
        "</div>",
        "</body></html>",
    ]
    return "\n".join(parts)


def _render_warnings(report: PortfolioReport) -> str:
    if not report.warnings:
        return ""
    items = "".join(f'<div class="warning">⚠ {escape(w)}</div>' for w in report.warnings)
    return f"<h2>경고</h2>{items}"


def _render_aggregates(report: PortfolioReport) -> str:
    agg = report.aggregates
    return (
        f"<h2>포트폴리오 집계</h2>"
        f'<div class="aggregates">'
        f"<b>총 평가금액:</b> {_fmt(agg.total_market_value, '원')}<br>"
        f"<b>가중 PER:</b> {_fmt(agg.weighted_per)} {_cov(agg.per_coverage)}<br>"
        f"<b>가중 추정 PER:</b> {_fmt(agg.weighted_forward_per)} {_cov(agg.forward_per_coverage)}<br>"
        f"<b>가중 베타 (52주):</b> {_fmt(agg.weighted_beta)} {_cov(agg.beta_coverage)}"
        f"</div>"
    )


def _render_holdings_table(report: PortfolioReport) -> str:
    rows = []
    portfolio = report.portfolio
    for h in portfolio.holdings:
        s = h.stock
        weight = portfolio.weight_of(h)
        rows.append(
            f"<tr><td>{escape(h.code)}</td><td>{escape(h.name)}</td>"
            f"<td>{h.quantity:g}</td>"
            f"<td>{_fmt(s.current_price if s else None, '원')}</td>"
            f"<td>{_fmt(h.market_value, '원')}</td>"
            f"<td>{weight:.1%}</td>"
            f"<td>{_fmt(s.per if s else None)}</td>"
            f"<td>{_fmt(s.forward_per if s else None)}</td>"
            f"<td>{_fmt(s.beta if s else None)}</td></tr>"
        )
    return (
        "<h2>보유 종목</h2>"
        "<table><thead><tr>"
        "<th>종목코드</th><th>종목명</th><th>수량</th><th>현재가</th><th>평가금액</th>"
        "<th>비중</th><th>PER</th><th>추정PER</th><th>베타</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _render_per_stock(report: PortfolioReport) -> str:
    if not report.per_stock_analyses:
        return ""
    parts = ["<h2>종목별 기술적 분석</h2>"]
    for ta in report.per_stock_analyses:
        parts.append(f"<h3>{escape(ta.code)} {escape(ta.name)}</h3>")
        parts.append(_render_signals_table(ta.indicators))
        if ta.chart_html:
            parts.append(ta.chart_html)
        if ta.llm_explanation:
            parts.append(
                f'<div style="background:#fff; padding:12px 16px; border-left:4px solid #3498db;">'
                f"<b>해석:</b><br>{escape(ta.llm_explanation)}</div>"
            )
    return "\n".join(parts)


def _render_signals_table(signals: dict) -> str:
    if not signals:
        return ""
    rows = []
    for name, data in signals.items():
        values = ", ".join(
            f"{k}={_fmt(v) if isinstance(v, (int, float)) else escape(str(v))}"
            for k, v in data.items()
            if k != "signal"
        )
        sig = escape(str(data.get("signal", "")))
        rows.append(
            f"<tr><td>{name.upper()}</td><td>{values}</td>"
            f"<td class='signal'>{sig}</td></tr>"
        )
    return (
        "<table><thead><tr><th>지표</th><th>수치</th><th>신호</th></tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody></table>"
    )


def _cov(cov: Coverage) -> str:
    excl = f", 제외: {', '.join(cov.excluded_codes)}" if cov.excluded_codes else ""
    return f'<span class="coverage">(커버리지 {cov.ratio:.1%}{excl})</span>'


def _fmt(value, suffix: str = "") -> str:
    if value is None:
        return "-"
    try:
        f = float(value)
    except (TypeError, ValueError):
        return escape(str(value))
    if abs(f) >= 1000:
        return f"{f:,.0f}{suffix}"
    return f"{f:.2f}{suffix}"
