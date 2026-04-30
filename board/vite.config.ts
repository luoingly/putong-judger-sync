// https://vitejs.dev/config/
import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
    extensions: [ '.mjs', '.js', '.ts', '.json', '.vue' ],
  },
  plugins: [
    tailwindcss(),
    vue(),
  ],
  css: {
    preprocessorOptions: {
      less: { javascriptEnabled: true },
    },
  },
})
