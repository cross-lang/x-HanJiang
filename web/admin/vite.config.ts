import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig(({ mode }) => {
  // 加载当前模式对应的环境变量文件（.env / .env.development / .env.production）
  const env = loadEnv(mode, process.cwd())
  // 开发代理目标：默认本机后端 8000，可在 .env.development 中通过 VITE_PROXY_TARGET 覆盖
  const proxyTarget = env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000'

  return {
    // 生产构建挂载到 Nginx /admin/ 子路径（同域部署）；开发环境保持根路径不变
    base: mode === 'production' ? '/admin/' : '/',
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
          target: proxyTarget,
          changeOrigin: true,
          // 开发环境模拟 Nginx 写入真实客户端 IP（后端 get_client_ip 只认 X-Real-IP）
          headers: { 'X-Real-IP': '127.0.0.1' },
        },
        '/docs': {
          target: proxyTarget,
          changeOrigin: true,
        },
        '/redoc': {
          target: proxyTarget,
          changeOrigin: true,
        },
        '/openapi.json': {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
    },
    build: {
      // 主包体积告警阈值（按需引入后主包预期 < 800KB）
      chunkSizeWarningLimit: 800,
      // 跳过构建结束的 gzip 体积统计，缩短构建耗时
      reportCompressedSize: false,
      // 小于 8KB 的静态资源内联为 base64，减少请求数（IP 直访场景降低建连开销）
      assetsInlineLimit: 8192,
      // 构建目标：ES2020 现代浏览器基线，兼顾语法降级与产物体积
      target: 'es2020',
      // 生产不输出 sourcemap：减小产物体积，避免暴露源码结构
      sourcemap: false,
      rollupOptions: {
        output: {
          // 产物按类型分目录并带内容指纹，配合 nginx 对静态资源的长缓存
          entryFileNames: 'assets/js/[name]-[hash].js',
          chunkFileNames: 'assets/js/[name]-[hash].js',
          assetFileNames: 'assets/[ext]/[name]-[hash].[ext]',
          manualChunks: {
            vendor: ['vue', 'vue-router', 'pinia', 'axios', 'dayjs'],
            'element-plus': ['element-plus'],
            echarts: ['echarts/core', 'vue-echarts'],
          },
        },
      },
    },
    // 生产压缩阶段移除 debugger 与调试性 console（保留 error / warn 便于线上排障）
    esbuild: {
      drop: ['debugger'],
      pure: ['console.log', 'console.info', 'console.debug'],
    },
  }
})
