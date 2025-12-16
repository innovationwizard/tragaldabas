import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(({ mode }) => {
  const baseUrl = process.env.VITE_BASE_URL || 'https://tragaldabas.com'
  
  return {
    plugins: [
      react(),
      // Replace BASE_URL placeholder in HTML during build
      {
        name: 'replace-base-url',
        transformIndexHtml: {
          order: 'pre',
          handler(html) {
            return html.replace(/__BASE_URL__/g, baseUrl)
          }
        }
      }
    ],
    resolve: {
      extensions: ['.js', '.jsx', '.json', '.ts', '.tsx'],
      alias: {
        '@': path.resolve(__dirname, './src')
      }
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
        '/ws': {
          target: 'ws://localhost:8000',
          ws: true,
        }
      }
    }
  }
})
