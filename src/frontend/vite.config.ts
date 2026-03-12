import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  base: './',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    host: '0.0.0.0',  // 允许外部访问
    port: 9000,
    strictPort: true,
    open: true  // 自动在浏览器中打开
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    assetsInlineLimit: 0 // 确保大文件不被内联
  },
  assetsInclude: ['**/*.fbx'] // 包含FBX文件
})
