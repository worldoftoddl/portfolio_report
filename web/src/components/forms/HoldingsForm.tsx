"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useFieldArray, useForm } from "react-hook-form";

import {
  portfolioFormSchema,
  type PortfolioFormInput,
  type PortfolioFormOutput,
} from "@/lib/schema";
import type { PortfolioAnalyzeRequest } from "@/types/api";

interface HoldingsFormProps {
  onSubmit: (req: PortfolioAnalyzeRequest) => void;
  isSubmitting?: boolean;
}

/**
 * 종목 입력 폼. 한 줄 = (종목명 또는 코드) + 수량.
 *
 * - react-hook-form + zodResolver로 클라이언트 사이드 검증
 * - useFieldArray로 행 추가/삭제
 * - 폼 값 → 백엔드 `PortfolioAnalyzeRequest`로 변환 후 `onSubmit` 호출
 */
export default function HoldingsForm({
  onSubmit,
  isSubmitting = false,
}: HoldingsFormProps) {
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<PortfolioFormInput, unknown, PortfolioFormOutput>({
    resolver: zodResolver(portfolioFormSchema),
    defaultValues: {
      holdings: [
        { name: "삼성전자", code: "", quantity: 10 },
        { name: "SK하이닉스", code: "", quantity: 5 },
      ],
      use_llm: false,
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: "holdings",
  });

  const submit = (values: PortfolioFormOutput) => {
    const req: PortfolioAnalyzeRequest = {
      holdings: values.holdings.map((h) => ({
        name: h.name?.trim() || null,
        code: h.code?.trim() || null,
        quantity: h.quantity,
      })),
      indicators: [],
      ohlcv_days: 180,
      use_llm: values.use_llm,
    };
    onSubmit(req);
  };

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-4">
      <div className="space-y-2">
        {fields.map((field, idx) => (
          <div key={field.id} className="flex gap-2 items-start">
            <div className="flex-1">
              <input
                {...register(`holdings.${idx}.name`)}
                placeholder="종목명 (예: 삼성전자)"
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
              />
              {errors.holdings?.[idx]?.name && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.holdings[idx]?.name?.message}
                </p>
              )}
            </div>
            <input
              {...register(`holdings.${idx}.code`)}
              placeholder="코드 (선택, 예: 005930)"
              className="w-40 rounded border border-gray-300 px-3 py-2 text-sm"
            />
            <div className="w-32">
              <input
                type="number"
                step="any"
                {...register(`holdings.${idx}.quantity`)}
                placeholder="수량"
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
              />
              {errors.holdings?.[idx]?.quantity && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.holdings[idx]?.quantity?.message}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={() => remove(idx)}
              disabled={fields.length <= 1}
              className="rounded border border-gray-300 px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 disabled:opacity-40"
            >
              삭제
            </button>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => append({ name: "", code: "", quantity: 1 })}
          className="rounded border border-dashed border-gray-400 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
        >
          + 종목 추가
        </button>

        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input type="checkbox" {...register("use_llm")} />
          LLM 해석 포함 (느려질 수 있음)
        </label>
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {isSubmitting ? "분석 중..." : "분석 시작"}
      </button>
    </form>
  );
}
