# syntax=docker/dockerfile:1.7
# Next.js 프런트 (개발 서버). 볼륨 마운트로 src/ 핫리로드.
FROM node:24-slim

WORKDIR /app

# 의존성 캐시
COPY package.json package-lock.json ./
RUN npm ci

# 나머지 설정 + 소스
COPY next.config.ts tsconfig.json eslint.config.mjs postcss.config.mjs ./
COPY public ./public
COPY src ./src

EXPOSE 3000

CMD ["npm", "run", "dev"]
