import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': new URL('./src', import.meta.url).pathname,
    },
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
  build: {
    // The embed's CSP allows `font-src 'self'` only, so a font inlined as a data: URI (KaTeX
    // ships some under the default 4 kB limit) would be blocked. Fonts are always emitted as files.
    assetsInlineLimit: (filePath) => (/\.(woff2?|ttf)$/.test(filePath) ? false : undefined),
    rollupOptions: {
      output: {
        entryFileNames: 'assets/widget-app.js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: (assetInfo) =>
          assetInfo.names.some((name) => name.endsWith('.css'))
            ? 'assets/widget-app.css'
            : 'assets/[name]-[hash][extname]',
      },
    },
  },
})
