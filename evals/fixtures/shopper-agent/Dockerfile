FROM mcr.microsoft.com/playwright:v1.47.2-jammy AS build
WORKDIR /app
COPY package.json package-lock.json tsconfig.json ./
RUN npm ci
COPY src ./src
RUN npm run build && npm prune --omit=dev

FROM mcr.microsoft.com/playwright:v1.47.2-jammy
WORKDIR /app
ENV NODE_ENV=production PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY package.json .mcp.json ./
COPY config ./config
COPY prompts ./prompts
COPY public ./public
# Consent-banner dismissal extension used by every browser context.
ADD https://github.com/cookieless-dev/autoconsent-ext/releases/latest/download/autoconsent.zip /opt/ext/autoconsent.zip
RUN cd /opt/ext && unzip -q autoconsent.zip && rm autoconsent.zip
USER pwuser
EXPOSE 8080
CMD ["node", "dist/server.js"]
