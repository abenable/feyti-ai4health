# Use the official Bun image for minimal size and incredible speed
FROM oven/bun:1.3.10-alpine AS deps
WORKDIR /app

# Install dependencies
COPY package.json bun.lock* ./
RUN bun install --frozen-lockfile

# Rebuild the source code only when needed
FROM oven/bun:1.3.10-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Internal backend URL baked into Next.js rewrites at build time (rewrites are
# evaluated during `next build`). Defaults to the compose service name.
ARG BACKEND_INTERNAL_URL=http://backend:8000
ENV BACKEND_INTERNAL_URL=${BACKEND_INTERNAL_URL}

# Disable telemetry during build
ENV NEXT_TELEMETRY_DISABLED=1

RUN bun run build

# Production image, copy all the files and run next
FROM oven/bun:1.3.10-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Don't run production as root
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001

COPY --from=builder /app/public ./public

# Automatically leverage output traces to reduce image size
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["bun", "server.js"]