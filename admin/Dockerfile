FROM node:22.17.1-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
# npm/cli#4828: `npm ci` against the locked tree fails to install the
# Alpine-musl rollup native binary (and refuses to resolve a transitive
# rolldown@1.x peer). Workaround: drop the lock, let npm install fresh
# inside the linux-musl image. Slower but reproducible across builds.
RUN rm -f package-lock.json && npm install --legacy-peer-deps
COPY . .
ARG BUILD_MODE=production
RUN npx vite build --mode $BUILD_MODE

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY ./nginx.conf /etc/nginx/conf.d/default.conf
