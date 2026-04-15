"use client";

import { useRouter } from "next/navigation";

import HoldingsForm from "@/components/forms/HoldingsForm";
import { usePortfolioAnalysis } from "@/hooks/usePortfolioAnalysis";
import { hashPortfolioRequest, saveReport } from "@/lib/reportStorage";

/**
 * 폼 제출 → mutation → 성공 시 sessionStorage에 저장 + `/report/[id]`로 이동.
 *
 * 결과 표시는 `/report/[id]` 페이지의 ReportView가 담당 (6e-4). 이 컴포넌트는
 * 이동 트리거 + 중간 상태(대기/에러)만 보여준다.
 */
export default function AnalyzePanel() {
  const router = useRouter();
  const mutation = usePortfolioAnalysis();

  return (
    <div className="space-y-4">
      <HoldingsForm
        onSubmit={(req) => {
          mutation.mutate(req, {
            onSuccess: (report) => {
              const id = hashPortfolioRequest(req);
              saveReport(id, {
                request: req,
                report,
                savedAt: new Date().toISOString(),
              });
              router.push(`/report/${id}`);
            },
          });
        }}
        isSubmitting={mutation.isPending}
      />

      {mutation.error && (
        <div className="rounded border border-red-300 bg-red-50 p-4 text-sm text-red-700">
          분석 실패: {mutation.error.message}
        </div>
      )}
    </div>
  );
}
