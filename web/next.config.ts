import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // rewrites 제거 (6e-1) — 브라우저가 localhost:3000 → localhost:8000으로
  // cross-origin 요청을 직접 보내도록 전환. 백엔드 `cors_origins`가 실검증됨.
  // API base URL은 `NEXT_PUBLIC_API_URL` 환경변수로 주입.
};

export default nextConfig;
