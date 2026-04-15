#!/usr/bin/env bash
# VCR 카세트 전체 갱신 — 네이버 HTML 구조 변경 대응 시 실행.
# 네트워크 호출이 일어나므로 IP 차단 주의.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

CASSETTES_DIR="tests/cassettes"

echo "[refresh_cassettes] 기존 카세트 삭제: $CASSETTES_DIR"
rm -f "$CASSETTES_DIR"/*.yaml

echo "[refresh_cassettes] 녹화 모드로 테스트 실행..."
PORTFOLIO_REPORT_VCR_RECORD=all uv run pytest tests/data/test_naver_client_vcr.py -v

echo "[refresh_cassettes] 재생 모드(none)로 검증..."
uv run pytest tests/data/test_naver_client_vcr.py -v

echo "[refresh_cassettes] ✓ 완료. git diff로 변경사항 확인 후 커밋하세요."
