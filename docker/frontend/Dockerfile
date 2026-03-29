# ebook-tools Frontend
# Multi-stage: Node 20 (pnpm build) → Nginx 1.27-alpine (serve)
#
# Build:  docker build -t ebook-tools-frontend -f docker/frontend/Dockerfile \
#           --build-arg VITE_API_BASE_URL=https://api.langtools.fifosk.synology.me \
#           --build-arg VITE_STORAGE_BASE_URL=https://api.langtools.fifosk.synology.me/storage .
# Run:    docker run -d -p 3080:80 -e BACKEND_HOST=192.168.x.x ebook-tools-frontend

# ── Stage 1: Build the SPA ──────────────────────────────────────────
FROM node:20-alpine AS builder

# Use /app as workdir to mirror the repo layout — the frontend imports
# ../../../modules/shared/assets_data.json (a relative path above web/).
WORKDIR /app

# Enable pnpm (matches package.json prebuild script)
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy package manifests first for dependency layer caching
COPY web/package.json web/pnpm-lock.yaml web/
RUN cd web && pnpm install --frozen-lockfile

# Copy shared assets that the frontend imports from outside web/
COPY modules/shared/ modules/shared/

# Copy the rest of the frontend source
COPY web/ web/

# Build-time args — Vite embeds these in the JS bundle
ARG VITE_API_BASE_URL
ARG VITE_STORAGE_BASE_URL
ARG VITE_GOOGLE_CLIENT_ID=""
ARG VITE_APPLE_CLIENT_ID=""
ARG VITE_APPLE_REDIRECT_URI=""
ARG VITE_APP_BRANCH="docker"

# Type-check and build (skip export-dist — only dist/ is needed for web)
RUN cd web && pnpm exec tsc -b && pnpm exec vite build

# ── Stage 2: Serve with Nginx ───────────────────────────────────────
FROM nginx:1.27-alpine

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy nginx config as a template — the official nginx:alpine image
# auto-processes /etc/nginx/templates/*.template through envsubst on
# startup, writing results to /etc/nginx/conf.d/.
COPY docker/frontend/nginx.conf /etc/nginx/templates/default.conf.template

# Copy built SPA from builder stage
COPY --from=builder /app/web/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
