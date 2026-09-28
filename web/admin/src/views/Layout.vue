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
        <GlobalSearch />
        <NotificationBell />
        <div class="ai-btn" @click="aiVisible = true">
          <div class="ai-entry">
            <el-icon :size="18"><MagicStick /></el-icon>
            <span>AI 助手</span>
          </div>
        </div>
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
      <el-main style="background: #f0f2f5; padding: 0; display: flex; flex-direction: column">
        <div style="background: #fff; padding: 12px 20px; border-bottom: 1px solid #e4e7ed; display: flex; align-items: center; gap: 12px">
          <el-button text @click="$router.push('/dashboard')">
            <el-icon style="margin-right: 4px"><Back /></el-icon>返回首页
          </el-button>
          <el-divider direction="vertical" />
          <span style="color: #606266; font-size: 14px">{{ pageTitle }}</span>
        </div>
        <div style="flex: 1; padding: 20px">
          <router-view />
        </div>
        <div class="app-footer">
          Copyright © {{ currentYear }} 汉江管理系统 All Rights Reserved
        </div>
      </el-main>
    </el-container>

    <!-- AI 助手聊天弹窗 -->
    <el-drawer v-model="aiVisible" title="AI 助手" size="420px" direction="rtl">
      <div style="display: flex; flex-direction: column; height: 100%">
        <div style="flex: 1; overflow-y: auto; padding: 12px; background: #f8f9fb; border-radius: 8px; margin-bottom: 12px">
          <div v-if="aiMessages.length === 0" style="text-align: center; color: #999; padding: 40px 0">
            <el-icon size="40" color="#c0c4cc"><MagicStick /></el-icon>
            <p style="margin-top: 12px">你好！我是 AI 助手，有什么可以帮你的？</p>
          </div>
          <div v-for="(msg, idx) in aiMessages" :key="idx" style="margin-bottom: 12px; display: flex; justify-content: flex-end">
            <div style="background: #409eff; color: #fff; padding: 8px 12px; border-radius: 8px; max-width: 80%">
              {{ msg.content }}
            </div>
          </div>
        </div>
        <div style="display: flex; gap: 8px">
          <el-input
            v-model="aiInput"
            placeholder="输入你的问题..."
            @keyup.enter="sendAiMessage"
          />
          <el-button type="primary" @click="sendAiMessage">发送</el-button>
        </div>
      </div>
    </el-drawer>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import GlobalSearch from '@/components/GlobalSearch.vue'
import NotificationBell from '@/components/NotificationBell.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const currentYear = new Date().getFullYear()
const aiVisible = ref(false)
const aiInput = ref('')
const aiMessages = ref<any[]>([])

function sendAiMessage() {
  if (!aiInput.value.trim()) return
  aiMessages.value.push({ role: 'user', content: aiInput.value })
  aiInput.value = ''
  // TODO: 后续接入 AI 接口
  setTimeout(() => {
    aiMessages.value.push({ role: 'assistant', content: 'AI 助手功能即将上线，敬请期待！' })
  }, 500)
}

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
.ai-btn {
  margin-right: 24px;
  cursor: pointer;
}
.ai-entry {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 40px;
  padding: 0 16px;
  border-radius: 20px;
  background: linear-gradient(135deg, #7c3aed 0%, #6366f1 100%);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  user-select: none;
  box-shadow: 0 2px 8px rgba(124, 58, 237, 0.3);
  transition: all 0.2s ease;
}
.ai-entry:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(124, 58, 237, 0.45);
  filter: brightness(1.06);
}
.app-footer {
  flex-shrink: 0;
  text-align: center;
  padding: 12px 0 20px;
  color: #909399;
  font-size: 12px;
  user-select: none;
}
</style>
