import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  base: "./",
  plugins: [
    VitePWA({
      registerType: 'prompt',
      injectRegister: 'auto',
      includeAssets: ['pwa-icon-192.png', 'pwa-icon-512.png'],
      manifest: {
        name: '抓大鹅',
        short_name: '抓大鹅',
        description: '在手机上离线也能玩的抓大鹅游戏',
        lang: 'zh-CN',
        start_url: './',
        scope: './',
        display: 'standalone',
        theme_color: '#253c2b',
        background_color: '#dde7d5',
        icons: [
          {
            src: 'pwa-icon-192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'pwa-icon-512.png',
            sizes: '512x512',
            type: 'image/png'
          }
        ]
      },
      workbox: {
        globPatterns: ['**/*.{html,js,css,png,mp3,glb,wasm}'],
        maximumFileSizeToCacheInBytes: 50 * 1024 * 1024,
        cleanupOutdatedCaches: true
      }
    })
  ]
})
