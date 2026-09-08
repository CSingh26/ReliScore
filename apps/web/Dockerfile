FROM node:22-alpine

RUN corepack enable

WORKDIR /workspace

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.base.json ./
COPY packages/shared/package.json packages/shared/package.json
COPY apps/web/package.json apps/web/package.json

RUN pnpm install --filter @reliscore/shared --filter @reliscore/web --frozen-lockfile

COPY packages/shared packages/shared
COPY apps/web apps/web

RUN pnpm --filter @reliscore/shared build
RUN pnpm --filter @reliscore/web build

WORKDIR /workspace/apps/web
EXPOSE 3000
CMD ["pnpm", "start", "-p", "3000"]
