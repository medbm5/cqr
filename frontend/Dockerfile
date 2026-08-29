# Build context is the repository root.
#
#   docker build -f frontend/Dockerfile -t citalid-risk-cockpit .
#
# Only used for local parity via docker-compose. On Vercel the frontend is built
# from `frontend/` directly and this file is ignored.

FROM node:20-alpine AS deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --omit=dev --ignore-scripts || npm install

FROM node:20-alpine AS builder
WORKDIR /app
# NEXT_PUBLIC_* is inlined into the client bundle at build time, so the API URL
# is a build argument rather than a runtime variable. Changing it means
# rebuilding - which is why the deployment notes tell you to set it on Vercel
# before the first deploy, not after.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup -g 10001 app && adduser -u 10001 -G app -D app
COPY --from=builder --chown=app:app /app ./
USER app
EXPOSE 3000
CMD ["npm", "run", "start"]
