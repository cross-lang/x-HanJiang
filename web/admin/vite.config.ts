import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig({
  // 生产构建挂载到 Nginx /admin/ 子路径（同域部署）；开发环境保持根路径不变
  base: process.env.NODE_ENV === 'production' ? '/admin/' : '/',
  plugins: [
    vue(),
    // Element Plus 按需引入：组件 + v-loading 等指令按需注册并注入样式
    Components({
      resolvers: [ElementPlusResolver()],
      directives: true,
      dts: 'src/components.d.ts',
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // 开发环境模拟 Nginx 写入真实客户端 IP（后端 get_client_ip 只认 X-Real-IP）
        headers: { 'X-Real-IP': '127.0.0.1' },
      },
      '/docs': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/redoc': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/openapi.json': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    // 主包体积告警阈值（按需引入后主包预期 < 800KB）
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['vue', 'vue-router', 'pinia', 'axios', 'dayjs'],
          'element-plus': ['element-plus'],
          echarts: ['echarts/core', 'vue-echarts'],
        },
      },
    },
  },
})
