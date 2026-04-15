import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 미니 프로젝트 한정 API 프록시 (6e 본편 첫 커밋 전에 제거 예정 — plan.md 참조)
  // 동일 출처로 보이므로 CORS는 실검증되지 않는다.
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
