from __future__ import annotations

import csv
from pathlib import Path

import yaml

from portfolio_report.models.holding import HoldingInput


def load_portfolio_file(path: Path) -> list[HoldingInput]:
    """YAML 또는 CSV에서 HoldingInput 리스트를 로드."""
    if not path.exists():
        raise FileNotFoundError(f"포트폴리오 파일을 찾을 수 없습니다: {path}")

    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        return _load_yaml(path)
    if suffix == ".csv":
        return _load_csv(path)
    raise ValueError(f"지원하지 않는 형식입니다: {suffix} (.yaml, .yml, .csv 만 지원)")


def _load_yaml(path: Path) -> list[HoldingInput]:
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict) or "holdings" not in raw:
        raise ValueError("YAML 파일은 최상위에 'holdings' 리스트를 포함해야 합니다")
    holdings = raw["holdings"]
    if not isinstance(holdings, list):
        raise ValueError("'holdings'는 리스트여야 합니다")
    return [HoldingInput(**_normalize_entry(item)) for item in holdings]


def _load_csv(path: Path) -> list[HoldingInput]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [HoldingInput(**_normalize_entry(row)) for row in reader]


def _normalize_entry(entry: dict) -> dict:
    """code가 숫자로 들어왔을 때 6자리 0-padded 문자열로 변환."""
    result: dict = {}
    for key, value in entry.items():
        if value is None or value == "":
            continue
        if key == "code":
            result["code"] = str(value).zfill(6)
        elif key == "name":
            result["name"] = str(value).strip()
        elif key == "quantity":
            result["quantity"] = float(value)
    return result
