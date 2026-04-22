import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { sentryVitePlugin } from '@sentry/vite-plugin'
import { visualizer } from 'rollup-plugin-visualizer'

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

  // Bundle analyser: always emit stats.html so CI can upload as artefact.
  const analyserPlugin = visualizer({
    filename: 'dist/bundle-stats.html',
    open: false,
    gzipSize: true,
    brotliSize: false,
    template: 'treemap',
  })

  return {
    plugins: [vue(), ...sentryPlugins, analyserPlugin],
    build: {
      sourcemap: 'hidden', // Sentry plugin uploads .map files; 'hidden' strips //# sourceMappingURL= so browsers can't fetch them
      // Performance budget: initial JS < 350 KB gzipped.
      // Split out heavy vendor chunks so the main entry chunk stays lean.
      rollupOptions: {
        output: {
          manualChunks: {
            // TipTap editor suite is large — isolate in its own chunk loaded lazily.
            // Note: @tiptap/pm has only subpath exports (no root entry), so it is
            // excluded here — its subpaths are bundled transitively via starter-kit.
            'vendor-tiptap': [
              '@tiptap/vue-3',
              '@tiptap/starter-kit',
            ],
            // PDF rendering (pdfjs) is only used on signing / lease pages
            'vendor-pdfjs': ['pdfjs-dist'],
            // Vue ecosystem core
            'vendor-vue': ['vue', 'vue-router', 'pinia'],
          },
        },
      },
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
