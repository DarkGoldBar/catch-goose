import { execSync } from 'node:child_process'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

function gitVersionPlugin() {
  let version = 'dev'
  try {
    version = execSync('git rev-parse --short=7 HEAD').toString().trim()
  } catch {
    // git not available or not a repo, keep fallback
  }

  return {
    name: 'git-version',
    transformIndexHtml(html) {
      return html.replace(
        /<meta name="version" content=".*?" \/>/,
        `<meta name="version" content="${version}" />`
      )
    }
  }
}

// https://vite.dev/config/
export default defineConfig({
  base: "./",
  plugins: [
    gitVersionPlugin(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: false,
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
        background_color: '#c0ef9a',
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
        globPatterns: ['**/*.{js,css,png,mp3,glb,wasm}'],
        maximumFileSizeToCacheInBytes: 50 * 1024 * 1024,
        cleanupOutdatedCaches: true,
        navigateFallback: null,
        runtimeCaching: [
          {
            urlPattern: ({ request }) => request.mode === 'navigate',
            handler: 'NetworkFirst',
            options: {
              cacheName: 'navigation-cache',
              networkTimeoutSeconds: 3
            }
          }
        ]
      }
    })
  ]
})
