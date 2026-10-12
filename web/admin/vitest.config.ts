/**
 * Vitest 独立配置（与 vite.config.ts 并行存在，互不影响）。
 *
 * 设计要点：
 *  - 仅承载测试所需能力：Vue SFC 编译（@vitejs/plugin-vue）+ happy-dom 浏览器环境；
 *  - 同步业务侧 '@' 别名，保证测试代码可与源码一样使用 '@/...' 导入；
 *  - 不复制 vite.config.ts 中的代理、压缩、按需引入等构建专属插件，避免污染测试运行；
 *  - 不开启 globals，测试代码统一从 'vitest' 显式导入 describe/it/expect/vi，
 *    这样 vue-tsc --noEmit 仍能正确校验 src 内的 *.spec.ts。
 */
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  // 与 vite.config.ts 保持一致的 Vue 插件，使 *.spec.ts 能直接 mount *.vue 组件
  plugins: [vue()],
  resolve: {
    alias: {
      // 源码中大量使用 '@/...'，测试环境必须同步该别名
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    // 组件测试需要 DOM 环境；happy-dom 轻量且 API 足够覆盖本项目用例
    environment: 'happy-dom',
    // 显式关闭全局注入，强制从 'vitest' 导入，利于类型检查
    globals: false,
    // 用例默认匹配 **/*.spec.ts（位于 src 内 __tests__ 目录）
    include: ['src/**/*.spec.ts'],
  },
})
