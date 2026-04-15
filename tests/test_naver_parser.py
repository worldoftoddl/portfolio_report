"""네이버 파서 단위 테스트. 실제 크롤링한 HTML/JSON 픽스처를 사용."""

from __future__ import annotations

import json
import math

import pytest

from portfolio_report.data.naver_parser import (
    parse_main_info,
    parse_snapshot,
    parse_wisereport,
)


class TestParseSnapshot:
    def test_samsung_current_price(self, read_fixture):
        payload = json.loads(read_fixture("naver/snapshot_005930.json"))
        result = parse_snapshot(payload)
        assert result["code"] == "005930"
        assert result["name"] == "삼성전자"
        assert result["current_price"] == 212000.0
        assert result["market_cap"] == 1_239_411_064_896_000.0

    def test_skhynix_current_price(self, read_fixture):
        payload = json.loads(read_fixture("naver/snapshot_000660.json"))
        result = parse_snapshot(payload)
        assert result["code"] == "000660"
        assert result["name"] == "SK하이닉스"
        assert result["current_price"] is not None
        assert result["current_price"] > 0

    def test_empty_payload_returns_nones(self):
        result = parse_snapshot({"datas": []})
        assert result["code"] == ""
        assert result["current_price"] is None
        assert result["market_cap"] is None


class TestParseMainInfo:
    def test_samsung(self, read_fixture):
        html = read_fixture("naver/main_005930.html")
        result = parse_main_info(html)
        assert result["per"] == 32.34
        assert result["forward_per"] == 6.00
        assert result["eps"] == 6564.0
        assert result["forward_eps"] == 36119.0

    def test_skhynix(self, read_fixture):
        html = read_fixture("naver/main_000660.html")
        result = parse_main_info(html)
        assert result["per"] == 19.35
        assert result["forward_per"] == 5.00
        assert result["eps"] == 58955.0
        assert result["forward_eps"] == 220159.0

    def test_missing_forward_per_returns_none(self):
        """추정PER이 'N/A'로 표시된 경우 None을 반환."""
        html = """
        <html><body>
          <em id="_per">15.00</em>
          <em id="_cns_per">N/A</em>
          <em id="_eps">1,000</em>
          <em id="_cns_eps">-</em>
        </body></html>
        """
        result = parse_main_info(html)
        assert result["per"] == 15.0
        assert result["forward_per"] is None
        assert result["eps"] == 1000.0
        assert result["forward_eps"] is None

    def test_negative_per(self):
        """적자 기업은 PER이 음수로 올 수 있음."""
        html = '<em id="_per">-12.50</em><em id="_eps">-500</em>'
        result = parse_main_info(html)
        assert result["per"] == -12.5
        assert result["eps"] == -500.0

    def test_all_missing_elements(self):
        html = "<html><body>no relevant ids</body></html>"
        result = parse_main_info(html)
        assert result["per"] is None
        assert result["forward_per"] is None
        assert result["eps"] is None
        assert result["forward_eps"] is None


class TestParseWisereport:
    def test_samsung_beta(self, read_fixture):
        html = read_fixture("naver/wisereport_005930.html")
        result = parse_wisereport(html)
        assert result["beta"] == 1.20

    def test_skhynix_beta(self, read_fixture):
        html = read_fixture("naver/wisereport_000660.html")
        result = parse_wisereport(html)
        assert result["beta"] is not None
        assert 0.5 < result["beta"] < 3.0

    def test_missing_beta_returns_none(self):
        html = """
        <table>
          <tr><th scope="row">52주베타</th><td class="num">N/A</td></tr>
        </table>
        """
        result = parse_wisereport(html)
        assert result["beta"] is None

    def test_beta_not_in_html(self):
        html = "<html><body>irrelevant</body></html>"
        result = parse_wisereport(html)
        assert result["beta"] is None


class TestToFloatEdgeCases:
    def test_garbage_text_returns_none(self):
        """숫자로 파싱 불가능한 문자열은 None."""
        html = '<em id="_per">not_a_number</em>'
        result = parse_main_info(html)
        assert result["per"] is None


def test_wisereport_th_without_td_returns_none():
    """<th>52주베타</th> 이후 <td> 형제가 없을 때 None."""
    html = "<table><tr><th scope='row'>52주베타</th></tr></table>"
    result = parse_wisereport(html)
    assert result["beta"] is None


def test_numeric_not_nan_for_valid_inputs(read_fixture):
    """정상 픽스처에 대해 반환된 수치가 NaN이 아님을 보장."""
    snap = parse_snapshot(json.loads(read_fixture("naver/snapshot_005930.json")))
    info = parse_main_info(read_fixture("naver/main_005930.html"))
    beta = parse_wisereport(read_fixture("naver/wisereport_005930.html"))
    for val in (snap["current_price"], info["per"], info["forward_per"], beta["beta"]):
        assert val is not None
        assert not math.isnan(val)
