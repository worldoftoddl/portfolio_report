from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.logging import RichHandler

from portfolio_report.analysis.aggregator import PortfolioAnalyzer
from portfolio_report.portfolio_loader import load_portfolio_file
from portfolio_report.reporting.console import render_console

app = typer.Typer(help="한국 주식 포트폴리오 분석 리포트")
console = Console()


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_path=False, rich_tracebacks=True)],
    )


@app.command()
def analyze(
    input: Annotated[Path, typer.Option("--input", "-i", help="포트폴리오 파일 (.yaml/.csv)")],
    indicators: Annotated[
        str,
        typer.Option(
            "--indicators",
            help="쉼표 구분 기술적 지표 (ichimoku,rsi,macd,bb). 비어있으면 지표 생략 (Phase 4)",
        ),
    ] = "",
    no_llm: Annotated[bool, typer.Option("--no-llm", help="LLM 해석 생략 (Phase 4)")] = False,
    output_format: Annotated[
        str,
        typer.Option("--format", "-f", help="출력 형식: console, markdown, html"),
    ] = "console",
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="출력 파일 경로"),
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """포트폴리오 분석을 실행하고 리포트를 출력합니다."""
    _setup_logging(verbose)

    inputs = load_portfolio_file(input)
    console.print(f"[bold]입력 종목 수:[/bold] {len(inputs)}")

    with console.status("[cyan]포트폴리오 데이터 수집 및 집계 중..."):
        analyzer = PortfolioAnalyzer()
        report = analyzer.analyze(inputs)

    if output_format == "console":
        render_console(report, console)
    else:
        console.print(f"[yellow]'{output_format}' 출력은 Phase 5에서 구현 예정.[/yellow]")

    _ = indicators, no_llm, output  # Phase 4/5에서 사용


if __name__ == "__main__":
    app()
