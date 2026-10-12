import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

/**
 * Vitest 独立配置（行为级测试）。
 * - 与 vite.config.ts 完全隔离：不复用其 server.proxy / build / unplugin-vue-components 等生产链路；
 * - 仅同步 src 别名 '@'，保证测试内 '...' 与源码一致解析；
 * - 不改动 tsconfig / vue-tsc / build / eslint 任何现有配置。
 */
export default defineConfig({
  plugins: [vue()],
  resolve: {
    // 与 vite.config.ts 保持一致：'@' 指向 ./src
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    // 用 happy-dom 提供 localStorage / window / document 等浏览器环境，无头且快
    environment: 'happy-dom',
    // 只收集工程顶层 tests/ 目录下的用例；不开启 globals，用例内显式从 'vitest' 导入
    include: ['tests/**/*.spec.ts'],
  },
})
