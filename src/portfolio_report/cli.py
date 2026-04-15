from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from portfolio_report.data.ticker_resolver import TickerResolver
from portfolio_report.portfolio_loader import load_portfolio_file

app = typer.Typer(help="한국 주식 포트폴리오 분석 리포트")
console = Console()


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
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
            help="쉼표 구분 기술적 지표 (ichimoku,rsi,macd,bb). 비어있으면 지표 생략",
        ),
    ] = "",
    no_llm: Annotated[bool, typer.Option("--no-llm", help="LLM 해석 생략")] = False,
    output_format: Annotated[
        str,
        typer.Option("--format", "-f", help="출력 형식: console, markdown, html"),
    ] = "console",
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="출력 파일 경로 (markdown/html에서 필요)"),
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """포트폴리오 분석을 실행하고 리포트를 출력합니다."""
    _setup_logging(verbose)

    inputs = load_portfolio_file(input)
    console.print(f"[bold]입력 종목 수:[/bold] {len(inputs)}")

    resolver = TickerResolver()
    resolved = []
    for item in inputs:
        try:
            r = resolver.resolve(item)
        except ValueError as e:
            console.print(f"[red]해석 실패:[/red] {e}")
            raise typer.Exit(code=1) from e
        for w in r.warnings:
            console.print(f"[yellow]⚠ {w}[/yellow]")
        resolved.append((r, item.quantity))

    _print_resolved_table(resolved)

    indicator_list = [s.strip() for s in indicators.split(",") if s.strip()]
    console.print(
        f"\n[dim]지표: {indicator_list or '없음'} / LLM: {'OFF' if no_llm else 'ON'}"
        f" / 형식: {output_format}[/dim]"
    )
    console.print(
        "[yellow]Phase 1 완료. 데이터 수집(Phase 2) 및 분석(Phase 3+)은 후속 구현 예정.[/yellow]"
    )
    _ = output  # Phase 5에서 사용


def _print_resolved_table(resolved: list) -> None:
    table = Table(title="해석된 보유 종목")
    table.add_column("종목코드")
    table.add_column("종목명")
    table.add_column("수량", justify="right")
    for r, qty in resolved:
        table.add_row(r.code, r.name, f"{qty:g}")
    console.print(table)


if __name__ == "__main__":
    app()
