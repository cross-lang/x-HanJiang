<template>
  <header class="header">
    <div class="header-left">
      <span class="page-title">{{ pageTitle }}</span>
    </div>
    <div class="header-right">
      <NotificationBell />
      <el-dropdown trigger="click" @command="$emit('command', $event)">
        <span class="user-entry">
          <el-avatar :size="28" class="user-avatar">{{ initial }}</el-avatar>
          <span class="user-name">{{ developerStore.profile?.name || developerStore.profile?.username || '开发者' }}</span>
          <el-icon><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">个人中心</el-dropdown-item>
            <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowDown } from '@element-plus/icons-vue'
import { useDeveloperStore } from '@/stores/developer'
import NotificationBell from '@/components/NotificationBell.vue'

defineEmits<{ command: [cmd: string] }>()

const route = useRoute()
const developerStore = useDeveloperStore()

const TITLES: Record<string, string> = {
  home: '首页',
  apps: '应用管理',
  docs: '开放接口',
  profile: '个人中心',
}

const pageTitle = computed(() => TITLES[route.path.split('/')[1] || 'home'] || '汉江（HanJiang）开放平台')
const initial = computed(() => (developerStore.profile?.name || 'D').charAt(0))
</script>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 20px;
  background: var(--hj-bg-card);
  border-bottom: 1px solid var(--hj-border-lighter);
}
.page-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--hj-text-title);
  letter-spacing: 0.3px;
}
.user-entry {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: var(--hj-text-regular);
  padding: 4px 10px;
  border-radius: 8px;
  transition: background 0.15s ease;
}
.user-entry:hover {
  background: var(--hj-bg-hover);
}
.user-avatar {
  background: linear-gradient(135deg, var(--hj-primary), var(--hj-primary-weak));
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  border: none;
}
.user-name {
  font-size: 14px;
  font-weight: 500;
}
</style>
