// @ts-check
import { defineConfig } from 'astro/config';
import vue from '@astrojs/vue';
import sitemap from '@astrojs/sitemap';
import mdx from '@astrojs/mdx';
import tailwindcss from '@tailwindcss/vite';
import { visualizer } from 'rollup-plugin-visualizer';

// https://astro.build/config
export default defineConfig({
  site: 'https://klikk.co.za',
  integrations: [
    vue(),
    sitemap(),
    mdx(),
  ],
  vite: {
    plugins: [
      tailwindcss(),
      // Bundle analyser: emit treemap report for CI artefact upload.
      // Performance budget: marketing LCP < 2.5s on 3G (SA mobile networks).
      visualizer({
        filename: 'dist/bundle-stats.html',
        open: false,
        gzipSize: true,
        brotliSize: false,
        template: 'treemap',
      }),
    ],
    build: {
      // Astro already splits per-page; manual chunks keep Vue islands lean.
      rollupOptions: {
        output: {
          manualChunks: {
            'vendor-vue': ['vue'],
          },
        },
      },
    },
  },
});
