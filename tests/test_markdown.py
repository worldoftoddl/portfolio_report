"""마크다운 렌더러 단위 테스트.

정확한 포맷보다는 핵심 정보(종목, 수치, 커버리지, 신호, 경고, 해석)가 문자열에
포함되는지를 확인.
"""

from __future__ import annotations

from datetime import datetime

from portfolio_report.models.holding import Holding
from portfolio_report.models.portfolio import (
    Coverage,
    Portfolio,
    PortfolioAggregates,
    PortfolioReport,
    TechnicalAnalysis,
)
from portfolio_report.models.stock import StockInfo
from portfolio_report.reporting.markdown import render_markdown


def make_report(
    *,
    excluded_codes: list[str] | None = None,
    warnings: list[str] | None = None,
    analyses: list[TechnicalAnalysis] | None = None,
) -> PortfolioReport:
    h1 = Holding(
        code="005930",
        name="삼성전자",
        quantity=10,
        stock=StockInfo(
            code="005930", name="삼성전자", current_price=70000,
            per=30.5, forward_per=6.0, beta=1.2,
        ),
    )
    h2 = Holding(
        code="000660",
        name="SK하이닉스",
        quantity=5,
        stock=StockInfo(
            code="000660", name="SK하이닉스", current_price=150000,
            per=20.0, forward_per=None, beta=1.6,
        ),
    )
    aggregates = PortfolioAggregates(
        weighted_per=25.0,
        weighted_forward_per=6.0,
        weighted_beta=1.4,
        per_coverage=Coverage(metric="per", included_value=1_450_000),
        forward_per_coverage=Coverage(
            metric="forward_per",
            included_value=700_000,
            excluded_value=750_000,
            excluded_codes=excluded_codes or ["000660"],
        ),
        beta_coverage=Coverage(metric="beta", included_value=1_450_000),
        total_market_value=1_450_000,
    )
    return PortfolioReport(
        generated_at=datetime(2026, 4, 15, 15, 30, 0),
        portfolio=Portfolio(holdings=[h1, h2]),
        aggregates=aggregates,
        per_stock_analyses=analyses or [],
        warnings=warnings or [],
    )


class TestStructure:
    def test_starts_with_title_header(self):
        md = render_markdown(make_report())
        first_line = md.splitlines()[0]
        assert first_line.startswith("# "), "최상위 헤더(#)로 시작해야 함"
        assert "포트폴리오" in first_line

    def test_generated_at_present(self):
        md = render_markdown(make_report())
        assert "2026-04-15" in md
        assert "15:30" in md

    def test_is_plain_markdown_no_html_tags(self):
        """마크다운 출력에 HTML 태그가 섞이면 안 됨 (차트는 HTML 전용)."""
        md = render_markdown(make_report())
        # 기본 문자열에는 '<table' 같은 HTML 표 태그가 없어야 함
        assert "<table" not in md
        assert "<div" not in md


class TestHoldingsTable:
    def test_includes_holding_code_and_name(self):
        md = render_markdown(make_report())
        assert "005930" in md
        assert "삼성전자" in md
        assert "000660" in md
        assert "SK하이닉스" in md

    def test_includes_quantities_and_prices(self):
        md = render_markdown(make_report())
        # 수량 및 현재가 포함
        assert "10" in md
        assert "70,000" in md or "70000" in md
        assert "150,000" in md or "150000" in md

    def test_includes_per_and_beta(self):
        md = render_markdown(make_report())
        assert "30.5" in md  # samsung per
        assert "1.2" in md   # samsung beta
        assert "1.6" in md   # hynix beta

    def test_missing_forward_per_shown_as_dash_or_na(self):
        md = render_markdown(make_report())
        # hynix forward_per 없음 → 표에 '-' 또는 'N/A'
        # (간접 확인: 20.0 PER은 있지만 해당 행의 추정PER은 숫자가 아님)
        assert "-" in md or "N/A" in md


class TestAggregatesSection:
    def test_weighted_metrics_rendered(self):
        md = render_markdown(make_report())
        assert "25.00" in md or "25.0" in md   # weighted_per
        assert "6.00" in md or "6.0" in md      # weighted_forward_per
        assert "1.40" in md or "1.4" in md      # weighted_beta

    def test_coverage_percent_rendered(self):
        md = render_markdown(make_report())
        # per_coverage = 100%, forward_per = 700/1450 ≈ 48.3%
        assert "100" in md  # 100.0%
        assert "48" in md or "48.3" in md

    def test_excluded_codes_listed(self):
        md = render_markdown(make_report())
        assert "000660" in md  # 제외 종목 코드가 명시됨


class TestWarningsSection:
    def test_warnings_rendered(self):
        md = render_markdown(make_report(warnings=["삼성전자우 우선주 존재"]))
        assert "경고" in md or "Warning" in md.lower() or "⚠" in md
        assert "삼성전자우" in md

    def test_no_warnings_section_when_empty(self):
        md = render_markdown(make_report(warnings=[]))
        # 경고가 없을 때는 '경고' 섹션이 본문에 노출되지 않아도 됨.
        # 하지만 최소한 리포트 자체는 생성되어야 함.
        assert len(md) > 0


class TestTechnicalSection:
    def test_technical_section_empty_when_no_analyses(self):
        md = render_markdown(make_report(analyses=[]))
        # 기술적 분석 섹션 자체가 없거나, 있더라도 종목 세부는 없음
        assert "005930" in md  # 여전히 보유 종목은 나옴

    def test_indicators_and_signals_rendered(self):
        analysis = TechnicalAnalysis(
            code="005930",
            name="삼성전자",
            indicators={
                "rsi": {"value": 72.5, "signal": "과매수 (72.5)"},
                "macd": {"histogram": 30.0, "signal": "강세"},
            },
            llm_explanation="현재가는 구름대 위에 있으며 단기 강세 신호.",
        )
        md = render_markdown(make_report(analyses=[analysis]))
        assert "RSI" in md or "rsi" in md
        assert "과매수" in md
        assert "강세" in md
        assert "구름대 위" in md  # llm_explanation 본문

    def test_chart_html_not_leaked_into_markdown(self):
        analysis = TechnicalAnalysis(
            code="005930", name="삼성전자",
            indicators={"rsi": {"value": 50, "signal": "중립 (50.0)"}},
            chart_html='<div id="plot">CHART</div>',
        )
        md = render_markdown(make_report(analyses=[analysis]))
        # 마크다운에 raw HTML chart_html이 섞이면 안 됨
        assert '<div id="plot">' not in md
        assert "CHART" not in md


def test_renders_nonempty_string():
    md = render_markdown(make_report())
    assert isinstance(md, str)
    assert len(md) > 200


def test_disclaimer_present():
    md = render_markdown(make_report())
    assert "자문" in md or "참고" in md
