"""rich 기반 콘솔 출력."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from portfolio_report.models.portfolio import Coverage, PortfolioReport


def render_console(report: PortfolioReport, console: Console) -> None:
    _render_holdings_table(report, console)
    console.print()
    _render_aggregates_panel(report, console)
    if report.warnings:
        console.print()
        console.print(Panel("\n".join(f"⚠ {w}" for w in report.warnings), title="경고"))


def _render_holdings_table(report: PortfolioReport, console: Console) -> None:
    table = Table(title="보유 종목 상세")
    for col in ("종목코드", "종목명", "수량", "현재가", "평가금액", "비중", "PER", "추정PER", "베타"):
        table.add_column(col, justify="right" if col not in ("종목코드", "종목명") else "left")

    portfolio = report.portfolio
    for h in portfolio.holdings:
        s = h.stock
        price = _fmt_num(s.current_price if s else None, "원")
        mv = _fmt_num(h.market_value, "원")
        weight = f"{portfolio.weight_of(h):.1%}" if h.market_value else "-"
        per = _fmt_num(s.per if s else None)
        fwd = _fmt_num(s.forward_per if s else None)
        beta = _fmt_num(s.beta if s else None)
        table.add_row(
            h.code, h.name, f"{h.quantity:g}", price, mv, weight, per, fwd, beta
        )
    console.print(table)


def _render_aggregates_panel(report: PortfolioReport, console: Console) -> None:
    agg = report.aggregates
    lines = [
        f"[bold]총 평가금액:[/bold] {_fmt_num(agg.total_market_value, '원')}",
        "",
        f"가중 PER        : {_fmt_num(agg.weighted_per)}  {_cov(agg.per_coverage)}",
        f"가중 추정 PER   : {_fmt_num(agg.weighted_forward_per)}  {_cov(agg.forward_per_coverage)}",
        f"가중 베타 (52주): {_fmt_num(agg.weighted_beta)}  {_cov(agg.beta_coverage)}",
    ]
    console.print(Panel("\n".join(lines), title="포트폴리오 집계", expand=False))


def _cov(cov: Coverage) -> str:
    excl = f" (제외: {', '.join(cov.excluded_codes)})" if cov.excluded_codes else ""
    return f"[dim]커버리지 {cov.ratio:.1%}{excl}[/dim]"


def _fmt_num(value: float | None, suffix: str = "") -> str:
    if value is None:
        return "[dim]-[/dim]"
    if abs(value) >= 1000:
        return f"{value:,.0f}{suffix}"
    return f"{value:.2f}{suffix}"
