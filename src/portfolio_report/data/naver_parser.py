"""네이버 증권 응답(JSON/HTML) → 구조화된 dict 변환 (순수 함수).

네트워크 IO를 포함하지 않음. 테스트 가능성을 위해 NaverClient와 분리.
"""

from __future__ import annotations

from typing import TypedDict

from bs4 import BeautifulSoup


class SnapshotResult(TypedDict, total=False):
    code: str
    name: str
    current_price: float | None
    market_cap: float | None


class MainInfoResult(TypedDict, total=False):
    per: float | None
    forward_per: float | None
    eps: float | None
    forward_eps: float | None


class WisereportResult(TypedDict, total=False):
    beta: float | None


def _to_float(value: object) -> float | None:
    """쉼표/공백/N/A 등을 안전하게 float으로 변환. 실패 시 None."""
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace(" ", "")
    if not text or text in {"-", "N/A", "n/a"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_snapshot(payload: dict) -> SnapshotResult:
    """polling.finance.naver.com 실시간 시세 JSON 파싱."""
    datas = payload.get("datas") or []
    if not datas:
        return SnapshotResult(
            code="", name="", current_price=None, market_cap=None
        )
    d = datas[0]
    return SnapshotResult(
        code=d.get("itemCode") or d.get("symbolCode") or "",
        name=d.get("stockName") or "",
        current_price=_to_float(d.get("closePriceRaw") or d.get("closePrice")),
        market_cap=_to_float(d.get("marketValueFullRaw")),
    )


def _find_text(soup: BeautifulSoup, element_id: str) -> str | None:
    el = soup.find(id=element_id)
    if el is None:
        return None
    return el.get_text(strip=True)


def parse_main_info(html: str) -> MainInfoResult:
    """finance.naver.com/item/main.naver HTML에서 PER/추정PER/EPS 파싱.

    의존하는 DOM 앵커:
        #_per, #_cns_per, #_eps, #_cns_eps
    """
    soup = BeautifulSoup(html, "lxml")
    return MainInfoResult(
        per=_to_float(_find_text(soup, "_per")),
        forward_per=_to_float(_find_text(soup, "_cns_per")),
        eps=_to_float(_find_text(soup, "_eps")),
        forward_eps=_to_float(_find_text(soup, "_cns_eps")),
    )


def parse_wisereport(html: str) -> WisereportResult:
    """navercomp.wisereport.co.kr HTML에서 52주베타 파싱.

    구조: `<th>52주베타</th>` 다음 `<td class="num">1.20</td>`
    """
    soup = BeautifulSoup(html, "lxml")
    for th in soup.find_all("th"):
        label = th.get_text(strip=True)
        if label == "52주베타":
            td = th.find_next_sibling("td")
            if td is not None:
                return WisereportResult(beta=_to_float(td.get_text(strip=True)))
            break
    return WisereportResult(beta=None)
