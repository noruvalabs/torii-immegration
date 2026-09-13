# Torii web image — Next.js standalone output, multi-stage.
#
# Built from the REPO ROOT, not apps/web: the pnpm lockfile lives at the workspace root, and
# a lockfile-less install would resolve fresh dependency versions on every CI build.
#   docker build -f apps/web/Dockerfile .
FROM node:22-alpine AS base
ENV PNPM_HOME="/pnpm" PATH="/pnpm:$PATH"
RUN corepack enable

FROM base AS deps
WORKDIR /app
# The workspace manifests only — dependencies stay cached until a package.json or the
# lockfile changes. apps/api and apps/ai are JS-dependency-free turbo wrappers, but pnpm
# needs their manifests for --frozen-lockfile to match the lockfile's importers.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/
COPY apps/api/package.json ./apps/api/
COPY apps/ai/package.json ./apps/ai/
RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile --filter web...

FROM base AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/web/node_modules ./apps/web/node_modules
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web ./apps/web
ENV NEXT_TELEMETRY_DISABLED=1
ARG NEXT_PUBLIC_GOOGLE_CLIENT_ID
ENV NEXT_PUBLIC_GOOGLE_CLIENT_ID=$NEXT_PUBLIC_GOOGLE_CLIENT_ID
RUN pnpm --filter web build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
# Standalone traces from the workspace root, so the server lands at apps/web/server.js and
# expects its public/ and .next/static siblings at that same path.
COPY --from=build /app/apps/web/public ./apps/web/public
COPY --from=build --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/apps/web/.next/static ./apps/web/.next/static
USER nextjs
EXPOSE 3000
ENV PORT=3000 HOSTNAME=0.0.0.0
# busybox wget, not `node -e fetch`. Booting a second Node runtime to probe the first costs
# ~2s of CPU on the deployment host — every 30s, forever — and under load it overran the old
# 5s timeout and flapped the container to `unhealthy` while it was serving traffic fine. That
# is not cosmetic: compose `up --wait` and nginx's `depends_on: service_healthy` both gate on
# this, so a flapping probe can fail a deploy and trigger a rollback of a good release.
# wget is already in the alpine base and costs ~0s.
#
# 127.0.0.1, not `localhost`: the server binds 0.0.0.0 (IPv4 only, per HOSTNAME above) while
# busybox wget resolves `localhost` to ::1 first and gets connection-refused. Same IPv6 trap
# as the one called out in infra/nginx/conf.d/torii.conf.
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:3000/api/health || exit 1
CMD ["node", "apps/web/server.js"]
