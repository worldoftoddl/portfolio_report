import { z } from "zod";

/**
 * 보유 종목 한 줄. 백엔드 `HoldingInput`과 계약이 일치.
 *
 * - name 또는 code 중 하나는 반드시 있어야 함 (`refine`)
 * - quantity는 0 초과 (백엔드 `Field(gt=0)`)
 */
export const holdingSchema = z
  .object({
    name: z.string().optional(),
    code: z.string().optional(),
    quantity: z.coerce.number().positive({ message: "수량은 0보다 커야 합니다" }),
  })
  .refine((v) => (v.name ?? "").trim() || (v.code ?? "").trim(), {
    message: "종목명 또는 종목코드 중 하나는 필수입니다",
    path: ["name"],
  });

export const portfolioFormSchema = z.object({
  holdings: z.array(holdingSchema).min(1, "한 종목 이상 입력하세요"),
  use_llm: z.boolean(),
});

// react-hook-form은 register된 input이 string을 내보내고(resolver 통과 전)
// zod resolver가 이를 변환(coerce)한다. input/output을 분리해야 타입 일치.
export type PortfolioFormInput = z.input<typeof portfolioFormSchema>;
export type PortfolioFormOutput = z.output<typeof portfolioFormSchema>;
