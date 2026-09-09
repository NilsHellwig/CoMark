# syntax=docker/dockerfile:1
FROM node:22-slim AS base
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app

# --- Dependencies ---
FROM base AS deps
COPY package.json package-lock.json ./
RUN npm ci

# --- Build ---
FROM base AS build
# next.config rewrites bake API_URL at build time; NEXT_PUBLIC_* are inlined too.
ARG API_URL="http://backend:8897"
ARG NEXT_PUBLIC_API_BASE_URL=""
ARG NEXT_PUBLIC_WS_BASE_URL="ws://localhost:8897"
ARG NEXT_PUBLIC_GOOGLE_ENABLED="false"
ENV API_URL=$API_URL \
    NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL \
    NEXT_PUBLIC_WS_BASE_URL=$NEXT_PUBLIC_WS_BASE_URL \
    NEXT_PUBLIC_GOOGLE_ENABLED=$NEXT_PUBLIC_GOOGLE_ENABLED
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# --- Runtime (Next standalone) ---
FROM base AS runtime
# HOSTNAME=0.0.0.0 overrides Docker's default (container id), so the standalone
# server binds all interfaces and the healthcheck can reach it on localhost.
ENV NODE_ENV=production PORT=8896 HOSTNAME=0.0.0.0
COPY --from=build /app/public ./public
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
EXPOSE 8896
CMD ["node", "server.js"]

# --- Dev (hot reload; used by docker-compose.override) ---
FROM base AS dev
ENV PORT=8896
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 8896
CMD ["npm", "run", "dev"]
