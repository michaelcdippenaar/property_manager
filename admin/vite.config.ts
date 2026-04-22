import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { sentryVitePlugin } from '@sentry/vite-plugin'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  // Only upload source maps during a real production/staging build when auth token is available.
  const sentryPlugins =
    env.SENTRY_AUTH_TOKEN && env.VITE_SENTRY_DSN && mode !== 'development'
      ? [
          sentryVitePlugin({
            org: env.SENTRY_ORG ?? 'klikk',
            project: env.SENTRY_PROJECT_ADMIN ?? 'klikk-admin',
            authToken: env.SENTRY_AUTH_TOKEN,
            release: {
              name: env.VITE_APP_RELEASE,
              inject: false, // injected via VITE_APP_RELEASE env var at build time
            },
            sourcemaps: {
              assets: './dist/**',
              ignore: ['node_modules/**'],
            },
            telemetry: false,
          }),
        ]
      : []

  return {
    plugins: [vue(), ...sentryPlugins],
    build: {
      sourcemap: 'hidden', // Sentry plugin uploads .map files; 'hidden' strips //# sourceMappingURL= so browsers can't fetch them
    },
    server: {
      host: '0.0.0.0',
      port: 5173,
      proxy: {
        '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
        '/graphql': { target: 'http://127.0.0.1:8000', changeOrigin: true },
        '/ws': { target: 'http://127.0.0.1:8000', changeOrigin: true, ws: true },
      },
    },
    define: {
      'process.env': {},
    },
  }
})
