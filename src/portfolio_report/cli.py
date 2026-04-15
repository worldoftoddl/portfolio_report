from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.logging import RichHandler

from portfolio_report.analysis.aggregator import PortfolioAnalyzer
from portfolio_report.analysis.technical import ALL_INDICATORS, Indicator
from portfolio_report.config import get_settings
from portfolio_report.portfolio_loader import load_portfolio_file
from portfolio_report.reporting.console import render_console
from portfolio_report.reporting.html import render_html

app = typer.Typer(help="한국 주식 포트폴리오 분석 리포트")
console = Console()


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_path=False, rich_tracebacks=True)],
    )


def _parse_indicators(raw: str) -> list[Indicator]:
    if not raw:
        return []
    items = [s.strip().lower() for s in raw.split(",") if s.strip()]
    invalid = [i for i in items if i not in ALL_INDICATORS]
    if invalid:
        raise typer.BadParameter(
            f"지원하지 않는 지표: {invalid}. 사용 가능: {list(ALL_INDICATORS)}"
        )
    return items  # type: ignore[return-value]


@app.command()
def analyze(
    input: Annotated[Path, typer.Option("--input", "-i", help="포트폴리오 파일 (.yaml/.csv)")],
    indicators: Annotated[
        str,
        typer.Option(
            "--indicators",
            help="쉼표 구분 기술적 지표 (ichimoku,rsi,macd,bb). 지정 시 HTML이 기본 출력",
        ),
    ] = "",
    no_llm: Annotated[bool, typer.Option("--no-llm", help="LLM 해석 생략 (Phase 4b)")] = False,
    output_format: Annotated[
        str,
        typer.Option("--format", "-f", help="출력 형식: console, html"),
    ] = "",
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="HTML 출력 파일 경로"),
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """포트폴리오 분석을 실행하고 리포트를 출력합니다."""
    _setup_logging(verbose)

    indicator_list = _parse_indicators(indicators)

    # 기본 포맷: 지표가 있으면 html, 없으면 console
    if not output_format:
        output_format = "html" if indicator_list else "console"

    inputs = load_portfolio_file(input)
    console.print(f"[bold]입력 종목 수:[/bold] {len(inputs)}")
    if indicator_list:
        console.print(f"[bold]기술적 지표:[/bold] {indicator_list}")

    with console.status("[cyan]포트폴리오 데이터 수집 및 집계 중..."):
        analyzer = PortfolioAnalyzer()
        report = analyzer.analyze(inputs, indicators=indicator_list)

    if output_format == "console":
        render_console(report, console)
        return

    if output_format == "html":
        html = render_html(report)
        target = output or _default_html_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        console.print(f"[green]✓ HTML 리포트 저장됨:[/green] {target}")
        return

    console.print(f"[red]지원하지 않는 형식: {output_format}[/red]")
    raise typer.Exit(code=1)


def _default_html_path() -> Path:
    reports = get_settings().reports_dir
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return reports / f"portfolio_{stamp}.html"


if __name__ == "__main__":
    app()
