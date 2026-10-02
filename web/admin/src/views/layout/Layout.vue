<template>
  <el-container class="app-shell">
    <SidebarMenu :collapsed="isCollapsed" @toggle="toggleMenu" />
    <!-- direction="vertical"：el-container 靠检测直接子组件是否为 el-header/el-footer 判断纵向；
         拆分后直接子组件是自定义 HeaderBar/MainArea，自动判断会失效导致横向并排，故显式声明 -->
    <el-container class="app-body" direction="vertical">
      <HeaderBar @open-ai="aiVisible = true" @command="handleCommand" />
      <MainArea />
    </el-container>
    <AiAssistantDrawer v-model:visible="aiVisible" />
  </el-container>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import SidebarMenu from './components/SidebarMenu.vue'
import HeaderBar from './components/HeaderBar.vue'
import MainArea from './components/MainArea.vue'
import AiAssistantDrawer from './components/AiAssistantDrawer.vue'

const router = useRouter()
const userStore = useUserStore()

// 左侧菜单折叠状态（持久化到 localStorage）
const isCollapsed = ref(localStorage.getItem('sidebar_collapsed') === '1')

function toggleMenu() {
  isCollapsed.value = !isCollapsed.value
  localStorage.setItem('sidebar_collapsed', isCollapsed.value ? '1' : '0')
}

// 小江 AI 助手抽屉显隐
const aiVisible = ref(false)

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
.app-shell {
  height: 100vh;
}
.app-body {
  min-width: 0;
}
</style>
