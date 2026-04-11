import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // Listen on all local IPs
    proxy: {
      // Proxy API requests to FastAPI backend
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      // Proxy static assets (thumbnails, etc.)
      '/static': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      // Proxy generated clips
      '/clips': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      // Proxy WebSockets
      '/ws': {
        target: 'ws://127.0.0.1:5000',
        ws: true,
      }
    }
  }
})
