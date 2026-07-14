FROM node:22-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm install

FROM node:22-alpine AS builder
WORKDIR /app
ARG INTERNAL_API_BASE_URL=http://backend:8000
# Next rewrites are generated at build time from INTERNAL_API_BASE_URL.
ENV INTERNAL_API_BASE_URL=$INTERNAL_API_BASE_URL
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
