FROM node:22.17.1-alpine AS build

WORKDIR /app
COPY website/package.json website/package-lock.json ./
RUN npm ci
COPY website/ .
COPY content/ /content/
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY website/nginx.conf /etc/nginx/conf.d/default.conf
