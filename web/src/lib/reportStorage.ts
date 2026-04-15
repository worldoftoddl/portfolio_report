import type {
  PortfolioAnalyzeRequest,
  PortfolioReport,
} from "@/types/api";

/**
 * 리포트를 브라우저 탭 단위로 보관.
 *
 * - `id = hash(inputs)` — 같은 입력으로 재분석해도 같은 URL을 돌려줄 수 있다
 * - sessionStorage에 `report:${id}` 키로 저장 (탭 내 새로고침 후에도 복구)
 * - 서버는 stateless — 리포트 URL을 다른 사람에게 공유할 수는 없다 (의도된 제한)
 */

const STORAGE_PREFIX = "report:";

export interface StoredReport {
  request: PortfolioAnalyzeRequest;
  report: PortfolioReport;
  savedAt: string;
}

/**
 * djb2 해시 (비-암호학적, 6자 안팎 base36). URL에 쓸 충분히 짧은 고유 식별자.
 */
export function hashPortfolioRequest(req: PortfolioAnalyzeRequest): string {
  const json = JSON.stringify(req);
  let h = 5381;
  for (let i = 0; i < json.length; i++) {
    h = ((h << 5) + h) ^ json.charCodeAt(i);
  }
  return (h >>> 0).toString(36);
}

export function saveReport(id: string, stored: StoredReport): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(STORAGE_PREFIX + id, JSON.stringify(stored));
}

export function loadReport(id: string): StoredReport | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(STORAGE_PREFIX + id);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredReport;
  } catch {
    return null;
  }
}
