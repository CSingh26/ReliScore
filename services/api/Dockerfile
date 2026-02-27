FROM node:20-alpine

RUN apk add --no-cache curl
RUN corepack enable

WORKDIR /workspace

COPY package.json pnpm-workspace.yaml tsconfig.base.json ./
COPY packages/shared/package.json packages/shared/package.json
COPY services/api/package.json services/api/package.json

RUN pnpm install --filter @reliscore/shared --filter @reliscore/api --no-frozen-lockfile

COPY packages/shared packages/shared
COPY services/api services/api

RUN pnpm --filter @reliscore/shared build
RUN pnpm --filter @reliscore/api prisma:generate
RUN pnpm --filter @reliscore/api build

WORKDIR /workspace/services/api
EXPOSE 4000
CMD ["sh", "-c", "pnpm prisma db push && node dist/main.js"]
