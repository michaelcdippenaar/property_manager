FROM node:22.17.1-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps && npm install @rollup/rollup-linux-x64-musl@4.60.3 --no-save
COPY . .
ARG BUILD_MODE=production
RUN npx vite build --mode $BUILD_MODE

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY ./nginx.conf /etc/nginx/conf.d/default.conf
