FROM node:20.17.0-bookworm-slim@sha256:3c2b7f9a1e04d5b86f6e2a9c7d1b0e4f58a3c6d9e2f1a0b7c4d8e5f6a9b2c3d1 AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY tsconfig.json ./
COPY src ./src
RUN npm run build && npm prune --omit=dev

FROM node:20.17.0-bookworm-slim@sha256:3c2b7f9a1e04d5b86f6e2a9c7d1b0e4f58a3c6d9e2f1a0b7c4d8e5f6a9b2c3d1
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY package.json .mcp.json ./
COPY prompts ./prompts
COPY config ./config
USER node
ENV NODE_ENV=production
CMD ["node", "dist/worker.js"]
