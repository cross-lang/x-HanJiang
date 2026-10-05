<template>
  <el-container class="app-shell">
    <SidebarMenu :collapsed="isCollapsed" @toggle="toggleMenu" />
    <el-container class="app-body" direction="vertical">
      <HeaderBar @command="handleCommand" />
      <MainArea />
      <footer class="app-footer">© {{ year }} 汉江开放平台 HanJiang Open Platform. All Rights Reserved.</footer>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDeveloperStore } from '@/stores/developer'
import SidebarMenu from './components/SidebarMenu.vue'
import HeaderBar from './components/HeaderBar.vue'
import MainArea from './components/MainArea.vue'

const router = useRouter()
const developerStore = useDeveloperStore()

const year = new Date().getFullYear()

// 左侧菜单折叠状态（持久化到 localStorage）
const isCollapsed = ref(localStorage.getItem('open_sidebar_collapsed') === '1')

function toggleMenu() {
  isCollapsed.value = !isCollapsed.value
  localStorage.setItem('open_sidebar_collapsed', isCollapsed.value ? '1' : '0')
}

onMounted(async () => {
  try {
    await developerStore.fetchProfile()
  } catch {
    router.push('/login')
  }
})

function handleCommand(cmd: string) {
  if (cmd === 'logout') {
    developerStore.logout()
    router.push('/login')
  } else if (cmd === 'profile') {
    router.push('/profile')
  }
}
</script>

<style scoped>
.app-shell {
  height: 100vh;
}
.app-body {
  min-width: 0;
}
.app-footer {
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--hj-text-secondary);
  background: var(--hj-bg-card);
  border-top: 1px solid var(--hj-border-lighter);
  letter-spacing: 0.3px;
}
</style>
