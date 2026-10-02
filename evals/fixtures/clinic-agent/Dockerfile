# syntax=docker/dockerfile:1.7
FROM node:22.11-bookworm-slim@sha256:3f1a8d2c9b7e4f6a5d0c8b1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY tsconfig.json ./
COPY src ./src
RUN npm run build && npm prune --omit=dev

FROM gcr.io/distroless/nodejs22-debian12:nonroot@sha256:9b2e4c6a8d0f1e3c5a7b9d1f3e5c7a9b1d3f5e7c9a1b3d5f7e9c1a3b5d7f9e1c
WORKDIR /app
ENV NODE_ENV=production \
    CLINIC_AGENT_ROOT=/app
COPY --from=build --chown=65532:65532 /app/node_modules ./node_modules
COPY --from=build --chown=65532:65532 /app/dist ./dist
COPY --chown=65532:65532 package.json ./
COPY --chown=65532:65532 prompts ./prompts
COPY --chown=65532:65532 config ./config
COPY --chown=65532:65532 release ./release
USER 65532:65532
EXPOSE 8080
CMD ["dist/server.js"]
