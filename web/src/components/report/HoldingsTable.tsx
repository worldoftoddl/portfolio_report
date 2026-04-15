import Link from "next/link";

import type { Holding } from "@/types/api";

/**
 * 보유 종목 테이블. 각 행의 종목명은 종목 상세 페이지로 링크된다.
 * 상세 페이지(`/report/[id]/stock/[code]`)는 6e-5에서 구현 — 지금은 링크만 선배치.
 */
export default function HoldingsTable({
  reportId,
  holdings,
}: {
  reportId: string;
  holdings: Holding[];
}) {
  return (
    <div className="overflow-x-auto rounded border border-gray-200">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-left text-xs text-gray-600">
          <tr>
            <th className="px-3 py-2 font-medium">종목명</th>
            <th className="px-3 py-2 font-medium">코드</th>
            <th className="px-3 py-2 text-right font-medium">수량</th>
            <th className="px-3 py-2 text-right font-medium">현재가</th>
            <th className="px-3 py-2 text-right font-medium">평가금액</th>
            <th className="px-3 py-2 text-right font-medium">PER</th>
            <th className="px-3 py-2 text-right font-medium">베타</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {holdings.map((h) => {
            const price = h.stock?.current_price ?? null;
            const marketValue = price !== null ? price * h.quantity : null;
            return (
              <tr key={h.code} className="hover:bg-gray-50">
                <td className="px-3 py-2">
                  <Link
                    href={`/report/${reportId}/stock/${h.code}`}
                    className="font-medium text-blue-700 hover:underline"
                  >
                    {h.name}
                  </Link>
                </td>
                <td className="px-3 py-2 text-gray-600">{h.code}</td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {h.quantity}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {price !== null ? price.toLocaleString() : "—"}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {marketValue !== null ? marketValue.toLocaleString() : "—"}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {h.stock?.per?.toFixed(2) ?? "—"}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {h.stock?.beta?.toFixed(2) ?? "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
