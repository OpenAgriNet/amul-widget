FROM node:22-bookworm-slim AS build

ARG TARGETARCH

WORKDIR /workspace
COPY package.json package-lock.json ./
COPY apps/widget-web/package.json apps/widget-web/package.json
COPY packages/contracts/package.json packages/contracts/package.json
RUN npm ci
RUN case "$TARGETARCH" in \
      amd64) native_arch="x64" ;; \
      arm64) native_arch="arm64" ;; \
      *) echo "Unsupported target architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac \
    && npm install --no-save \
      "@tailwindcss/oxide-linux-${native_arch}-gnu@4.3.3" \
      "lightningcss-linux-${native_arch}-gnu@1.33.0"

COPY apps/widget-web apps/widget-web
COPY packages/contracts packages/contracts
RUN npm run build:web

FROM nginxinc/nginx-unprivileged:1.27-alpine

COPY apps/widget-web/nginx.conf /etc/nginx/nginx.conf
COPY --from=build /workspace/apps/widget-web/dist /usr/share/nginx/html

EXPOSE 8080
