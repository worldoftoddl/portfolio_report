from __future__ import annotations

import difflib
import logging
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache

import pandas as pd

from portfolio_report.config import Settings, get_settings
from portfolio_report.models.holding import HoldingInput

logger = logging.getLogger(__name__)

_MASTER_CACHE_KEY = "ticker_master_v1"


@dataclass(frozen=True)
class ResolvedTicker:
    code: str
    name: str
    warnings: list[str]


def _load_master_from_fdr() -> pd.DataFrame:
    """FinanceDataReader로 KRX 전체 종목 마스터를 수집 (1순위)."""
    import FinanceDataReader as fdr

    raw = fdr.StockListing("KRX")
    # Market: STK=KOSPI, KSQ=KOSDAQ, KNX=KONEX
    market_map = {"STK": "KOSPI", "KSQ": "KOSDAQ", "KNX": "KONEX"}
    df = pd.DataFrame(
        {
            "code": raw["Code"].astype(str).str.zfill(6),
            "name": raw["Name"],
            "market": raw["MarketId"].map(market_map).fillna(raw["MarketId"]),
        }
    )
    df = df.drop_duplicates(subset="code").reset_index(drop=True)
    logger.info("종목 마스터 로드 완료 (FDR): %d개", len(df))
    return df


def _load_master_from_pykrx() -> pd.DataFrame:
    """pykrx 폴백 (FDR 실패 시)."""
    from pykrx import stock

    today = datetime.now().strftime("%Y%m%d")
    rows: list[dict] = []
    for market in ("KOSPI", "KOSDAQ"):
        codes = stock.get_market_ticker_list(today, market=market)
        for code in codes:
            name = stock.get_market_ticker_name(code)
            rows.append({"code": code, "name": name, "market": market})
    df = pd.DataFrame(rows).drop_duplicates(subset="code").reset_index(drop=True)
    logger.info("종목 마스터 로드 완료 (pykrx): %d개", len(df))
    return df


def _load_master() -> pd.DataFrame:
    try:
        return _load_master_from_fdr()
    except Exception as e:
        logger.warning("FDR 마스터 로드 실패, pykrx로 폴백: %s", e)
        return _load_master_from_pykrx()


@lru_cache(maxsize=1)
def _get_master_cached() -> pd.DataFrame:
    """프로세스 수명 동안 마스터 데이터프레임 캐시."""
    import pickle

    from diskcache import Cache

    settings = get_settings()
    with Cache(str(settings.cache_dir)) as cache:
        cached = cache.get(_MASTER_CACHE_KEY)
        if cached is not None:
            return pickle.loads(cached)
        df = _load_master()
        cache.set(
            _MASTER_CACHE_KEY,
            pickle.dumps(df),
            expire=settings.cache_ticker_master_ttl_sec,
        )
        return df


class TickerResolver:
    """종목명/코드 입력을 표준 (code, name) 쌍으로 해석."""

    def __init__(self, settings: Settings | None = None, master: pd.DataFrame | None = None):
        self.settings = settings or get_settings()
        self._master = master

    @property
    def master(self) -> pd.DataFrame:
        if self._master is None:
            self._master = _get_master_cached()
        return self._master

    def resolve(self, item: HoldingInput) -> ResolvedTicker:
        warnings: list[str] = []

        if item.code:
            row = self.master.loc[self.master["code"] == item.code]
            if row.empty:
                raise ValueError(f"종목코드 {item.code}을(를) 찾을 수 없습니다")
            resolved_name = row.iloc[0]["name"]
            if item.name and item.name != resolved_name:
                warnings.append(
                    f"입력 이름 '{item.name}'과 종목코드 {item.code}의 실제 이름"
                    f" '{resolved_name}'이(가) 다릅니다. 실제 이름을 사용합니다."
                )
            return ResolvedTicker(code=item.code, name=resolved_name, warnings=warnings)

        assert item.name is not None
        exact = self.master.loc[self.master["name"] == item.name]
        if len(exact) == 1:
            row = exact.iloc[0]
            self._warn_preferred_stock_conflict(item.name, warnings)
            return ResolvedTicker(code=row["code"], name=row["name"], warnings=warnings)

        if len(exact) > 1:
            candidates = ", ".join(f"{r['code']}({r['market']})" for _, r in exact.iterrows())
            raise ValueError(
                f"동일 이름 '{item.name}'이(가) 여러 시장에 존재합니다: {candidates}. "
                "종목코드를 직접 입력하세요."
            )

        # fuzzy match
        candidates = difflib.get_close_matches(
            item.name, self.master["name"].tolist(), n=3, cutoff=0.75
        )
        if not candidates:
            raise ValueError(f"종목명 '{item.name}'을(를) 찾을 수 없습니다")
        raise ValueError(
            f"종목명 '{item.name}'을(를) 찾을 수 없습니다. 유사한 종목: {candidates}"
        )

    def _warn_preferred_stock_conflict(self, name: str, warnings: list[str]) -> None:
        """'삼성전자'를 입력했을 때 '삼성전자우'도 존재하면 경고."""
        if name.endswith("우"):
            return
        preferred_names = {f"{name}우", f"{name}우B", f"{name}1우"}
        existing = self.master.loc[self.master["name"].isin(preferred_names), "name"].tolist()
        if existing:
            warnings.append(
                f"보통주 '{name}'으로 해석했습니다. 우선주도 상장되어 있습니다: {existing}. "
                "우선주를 의도한 경우 종목코드를 직접 지정하세요."
            )
