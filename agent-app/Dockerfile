FROM node:22.17.1-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ENV NODE_ENV=production
# Baked into Quasar env (axios baseURL); override at build time if needed
ARG API_URL=https://backend.klikk.co.za/api/v1
ENV API_URL=${API_URL}
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist/spa /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
