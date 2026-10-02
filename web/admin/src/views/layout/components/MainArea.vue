<template>
  <el-main class="main-area">
    <div v-if="!isHome" class="page-head">
      <el-button text @click="$router.push('/dashboard')">
        <el-icon class="back-icon"><Back /></el-icon>返回首页
      </el-button>
      <el-divider direction="vertical" />
      <span class="page-title">{{ pageTitle }}</span>
    </div>
    <div class="page-body">
      <router-view />
    </div>
    <div class="app-footer">
      <div class="app-footer-links">
        <a href="https://github.com/cross-lang/x-HanJiang" target="_blank" rel="noopener noreferrer" title="GitHub">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
            <path
              d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"
            />
          </svg>
        </a>
        <a href="https://gitee.com/cross-lang/x-HanJiang" target="_blank" rel="noopener noreferrer" title="Gitee">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
            <path
              d="M2 6.5A4.5 4.5 0 0 1 6.5 2h11A4.5 4.5 0 0 1 22 6.5v11a4.5 4.5 0 0 1-4.5 4.5h-11A4.5 4.5 0 0 1 2 17.5v-11z"
            />
            <path fill="#fff" d="M5 9h14v1.3H5zm0 3.5h10v1.3H5z" />
          </svg>
        </a>
      </div>
      <span>Copyright © {{ currentYear }} 汉江管理系统 All Rights Reserved</span>
    </div>
  </el-main>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import type { MenuItem } from '@/types/auth'

const route = useRoute()
const userStore = useUserStore()

const currentYear = new Date().getFullYear()

// 当前是否为首页（/dashboard 或根路径 /）
const isHome = computed(() => route.path === '/dashboard' || route.path === '/')

const pageTitle = computed(() => {
  // 从菜单树里找当前路由对应的标题
  const findTitle = (list: MenuItem[], path: string): string => {
    for (const item of list) {
      if (item.path === path) return item.title
      if (item.children) {
        const found = findTitle(item.children, path)
        if (found) return found
      }
    }
    return ''
  }
  const titleMap: Record<string, string> = { '/profile': '个人中心' }
  return findTitle(userStore.menus, route.path) || titleMap[route.path] || route.path
})
</script>

<style scoped>
.main-area {
  background: #f0f2f5;
  padding: 0;
  display: flex;
  flex-direction: column;
}
.page-head {
  background: #fff;
  padding: 12px 20px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.back-icon {
  margin-right: 4px;
}
.page-title {
  color: #606266;
  font-size: 14px;
}
.page-body {
  flex: 1;
  padding: 20px;
}
.app-footer {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  padding: 12px 0 20px;
  color: #909399;
  font-size: 12px;
  user-select: none;
}
.app-footer-links {
  position: absolute;
  left: 24px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  gap: 14px;
}
.app-footer-links a {
  color: #909399;
  display: inline-flex;
  align-items: center;
  transition: color 0.15s;
}
.app-footer-links a:hover {
  color: #409eff;
}
</style>
