FROM node:22.21-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_DATA_MODE=api
ARG VITE_API_BASE_URL=
ENV VITE_DATA_MODE=${VITE_DATA_MODE} \
    VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

FROM nginx:1.31-alpine

ENV PORT=8080 \
    CMSQI_BACKEND_URL=http://backend:8000

COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=6 \
  CMD wget --quiet --tries=1 --spider "http://127.0.0.1:${PORT:-8080}/" || exit 1
