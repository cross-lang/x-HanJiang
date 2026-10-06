<template>
  <header class="header">
    <div class="header-left">
      <span class="page-title">{{ pageTitle }}</span>
    </div>
    <div class="header-right">
      <GlobalSearch />
      <NotificationBell />
      <el-dropdown trigger="hover" :hide-on-click="false" @command="$emit('command', $event)">
        <span class="user-entry">
          <el-avatar :size="32" class="user-avatar">{{ initial }}</el-avatar>
          <span class="user-meta">
            <span class="user-name">{{ developerStore.profile?.name || developerStore.profile?.username || '开发者' }}</span>
            <span v-if="developerStore.profile?.email" class="user-email">{{ developerStore.profile.email }}</span>
          </span>
          <el-icon class="entry-arrow"><ArrowDown /></el-icon>
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
import GlobalSearch from '@/components/GlobalSearch.vue'
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

const pageTitle = computed(() => TITLES[route.path.split('/')[1] || 'home'] || '汉江开放平台')
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
.header-right {
  display: flex;
  align-items: center;
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
.user-entry:hover .user-name {
  color: var(--hj-primary);
}
.user-entry:hover .entry-arrow {
  transform: rotate(180deg);
  color: var(--hj-primary);
}
.user-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1px;
  line-height: 1.25;
}
.user-avatar {
  background: linear-gradient(135deg, var(--hj-primary), var(--hj-primary-weak));
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  border: none;
  transition: transform 0.15s ease;
}
.user-entry:hover .user-avatar {
  transform: scale(1.06);
}
.user-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--hj-text-title);
  transition: color 0.15s ease;
}
.user-email {
  font-size: 12px;
  color: var(--hj-text-muted);
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.entry-arrow {
  font-size: 12px;
  transition: transform 0.15s ease, color 0.15s ease;
}
</style>
