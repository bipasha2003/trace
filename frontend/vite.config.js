import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

/**
 * Local runs the dev server (`npm run dev`); production serves the built bundle
 * with `vite preview` behind the Cloudflare tunnel. start.sh picks which — this
 * file never looks at APP_ENV. It only needs PRODUCTION_URL from the root .env
 * to accept that hostname.
 */
export default defineConfig(({ mode }) => {
  // Root .env, all keys. Config-time only — nothing here reaches the client bundle.
  const rootEnv = loadEnv(mode, path.resolve(__dirname, '..'), '')
  const domain = (rootEnv.PRODUCTION_URL || '').replace(/^https?:\/\//, '').replace(/\/+$/, '')
  const allowedHosts = domain ? [domain, `www.${domain}`] : []

  const apiProxy = {
    '/api': {
      target: process.env.VITE_API_TARGET || 'http://localhost:8000',
      changeOrigin: true,
      ws: true,
    },
  }

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 5173,
      host: true,
      proxy: apiProxy,
    },
    preview: {
      port: 5173,
      strictPort: true,
      host: '127.0.0.1', // reached only through the tunnel
      allowedHosts,
      proxy: apiProxy,
    },
  }
})
