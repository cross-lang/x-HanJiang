<template>
  <el-container style="height: 100vh">
    <el-aside
      :width="isCollapsed ? '64px' : '200px'"
      style="background: #ffffff; border-right: 1px solid #e4e7ed; position: relative; transition: width 0.25s ease; overflow: hidden"
    >
      <div
        class="app-title"
        :title="isCollapsed ? '点击展开菜单' : '点击收起菜单'"
        @click="toggleMenu"
      >
        {{ isCollapsed ? '汉江' : '汉江管理系统' }}
      </div>
      <el-menu
        :default-active="$route.path"
        background-color="#ffffff"
        text-color="#5a5e66"
        active-text-color="#409eff"
        router
        :collapse="isCollapsed"
        :collapse-transition="false"
      >
        <template v-for="menu in menus" :key="menu.id">
          <!-- 目录：有子菜单 -->
          <el-sub-menu v-if="menu.children && menu.children.length > 0" :index="String(menu.id)">
            <template #title>
              <el-icon><component :is="menu.icon" /></el-icon>
              <span>{{ menu.title }}</span>
            </template>
            <el-menu-item v-for="child in menu.children" :key="child.id" :index="child.path">
              <el-icon><component :is="child.icon" /></el-icon>
              <span>{{ child.title }}</span>
            </el-menu-item>
          </el-sub-menu>
          <!-- 菜单：直接可点击 -->
          <el-menu-item v-else :index="menu.path">
            <el-icon><component :is="menu.icon" /></el-icon>
            <span>{{ menu.title }}</span>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header style="background: #fff; border-bottom: 1px solid #eee; display: flex; justify-content: flex-end; align-items: center">
        <NotificationBell />
        <el-dropdown @command="handleCommand">
          <span style="cursor: pointer; display: flex; align-items: center; gap: 10px">
            <el-avatar :size="36" style="background: #79bbff">
              {{ (userStore.userInfo?.name || userStore.userInfo?.username || 'U').charAt(0) }}
            </el-avatar>
            <div style="line-height: 1.4">
              <div style="font-weight: 500; color: #333">{{ userStore.userInfo?.name || userStore.userInfo?.username || '用户' }}</div>
              <div style="font-size: 12px; color: #999">{{ userStore.userInfo?.email || '' }}</div>
            </div>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile"><el-icon style="margin-right: 8px"><User /></el-icon>个人中心</el-dropdown-item>
              <el-dropdown-item divided>
                <a href="https://github.com/cross-lang/x-HanJiang" target="_blank" style="display: flex; align-items: center; gap: 8px; color: inherit; text-decoration: none; line-height: 32px">
                  <el-icon><Link /></el-icon> GitHub
                </a>
              </el-dropdown-item>
              <el-dropdown-item>
                <a href="https://gitee.com/cross-lang/x-HanJiang" target="_blank" style="display: flex; align-items: center; gap: 8px; color: inherit; text-decoration: none; line-height: 32px">
                  <el-icon><Star /></el-icon> Gitee
                </a>
              </el-dropdown-item>
              <el-dropdown-item divided command="logout"><el-icon style="margin-right: 8px"><SwitchButton /></el-icon>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main style="background: #f0f2f5; padding: 0">
        <div style="background: #fff; padding: 12px 20px; border-bottom: 1px solid #e4e7ed; display: flex; align-items: center; gap: 12px">
          <el-button text @click="$router.push('/dashboard')">
            <el-icon style="margin-right: 4px"><Back /></el-icon>返回首页
          </el-button>
          <el-divider direction="vertical" />
          <span style="color: #606266; font-size: 14px">{{ pageTitle }}</span>
        </div>
        <div style="padding: 20px">
          <router-view />
        </div>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import NotificationBell from '@/components/NotificationBell.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 左侧菜单折叠状态（持久化到 localStorage）
const isCollapsed = ref(localStorage.getItem('sidebar_collapsed') === '1')

function toggleMenu() {
  isCollapsed.value = !isCollapsed.value
  localStorage.setItem('sidebar_collapsed', isCollapsed.value ? '1' : '0')
}

const menus = computed(() => userStore.menus)

const pageTitle = computed(() => {
  // 从菜单树里找当前路由对应的标题
  const findTitle = (list: any[], path: string): string => {
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
  return findTitle(menus.value, route.path) || titleMap[route.path] || route.path
})

onMounted(async () => {
  try {
    await userStore.fetchUserInfo()
    await userStore.fetchMenus()
  } catch {
    router.push('/login')
  }
})

function handleCommand(cmd: string) {
  if (cmd === 'logout') {
    userStore.logout()
    router.push('/login')
  } else if (cmd === 'profile') {
    router.push('/profile')
  }
}
</script>

<style scoped>
.app-title {
  color: #303133;
  text-align: center;
  padding: 20px 0;
  font-size: 18px;
  font-weight: bold;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  transition: color 0.2s ease, background-color 0.2s ease;
}
.app-title:hover {
  color: #409eff;
  background-color: #f5f7fa;
}
</style>
