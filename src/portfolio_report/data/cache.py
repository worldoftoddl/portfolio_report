"""diskcache 기반 영속 캐시 계층.

캐시 종류별 TTL을 분리:
- 가격: 장중(intraday) 5분, 장 마감 후(EOD) 12시간
- 펀더멘털(PER/추정PER/베타): 1일
- 종목 마스터: 7일
"""

from __future__ import annotations

from datetime import datetime, time
from functools import wraps
from typing import Callable, TypeVar
from zoneinfo import ZoneInfo

from diskcache import Cache

from portfolio_report.config import Settings, get_settings

T = TypeVar("T")

_KST = ZoneInfo("Asia/Seoul")
_MARKET_OPEN = time(9, 0)
_MARKET_CLOSE = time(15, 30)


def is_market_open(now: datetime | None = None) -> bool:
    """한국 증시 장중 여부 판정 (KST 09:00~15:30 평일).

    공휴일은 반영하지 않음. TTL 선택 힌트용이라 false positive 허용.
    """
    n = now or datetime.now(tz=_KST)
    if n.tzinfo is None:
        n = n.replace(tzinfo=_KST)
    n_kst = n.astimezone(_KST)
    if n_kst.weekday() >= 5:  # 토/일
        return False
    t = n_kst.time()
    return _MARKET_OPEN <= t <= _MARKET_CLOSE


def price_ttl(settings: Settings | None = None) -> int:
    s = settings or get_settings()
    return s.cache_price_intraday_ttl_sec if is_market_open() else s.cache_price_eod_ttl_sec


def fundamental_ttl(settings: Settings | None = None) -> int:
    s = settings or get_settings()
    return s.cache_fundamental_ttl_sec


def ticker_master_ttl(settings: Settings | None = None) -> int:
    s = settings or get_settings()
    return s.cache_ticker_master_ttl_sec


_cache_singleton: Cache | None = None


def get_cache(settings: Settings | None = None) -> Cache:
    global _cache_singleton
    if _cache_singleton is None:
        s = settings or get_settings()
        _cache_singleton = Cache(str(s.cache_dir))
    return _cache_singleton


def cached(namespace: str, ttl_fn: Callable[[], int]) -> Callable:
    """호출 결과를 namespace:key_args 형태로 캐시하는 데코레이터.

    key는 positional args + sorted kwargs 문자열 해시.
    """

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @wraps(fn)
        def wrapper(*args, **kwargs) -> T:
            cache = get_cache()
            key_parts = [namespace, fn.__name__, *map(repr, args)]
            if kwargs:
                key_parts.extend(f"{k}={v!r}" for k, v in sorted(kwargs.items()))
            key = "|".join(key_parts)
            hit = cache.get(key, default=_SENTINEL)
            if hit is not _SENTINEL:
                return hit  # type: ignore[return-value]
            value = fn(*args, **kwargs)
            cache.set(key, value, expire=ttl_fn())
            return value

        return wrapper

    return decorator


_SENTINEL = object()
