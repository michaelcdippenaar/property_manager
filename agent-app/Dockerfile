FROM node:22.17.1-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps
COPY . .

# BUILD_MODE selects which .env.* file to use (development | staging | production)
# Quasar/Vite reads .env.production at build time, so we copy the right file into place.
ARG BUILD_MODE=production
RUN if [ -f ".env.${BUILD_MODE}" ]; then cp ".env.${BUILD_MODE}" .env.production; fi
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist/spa /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
