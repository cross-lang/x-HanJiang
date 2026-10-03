<template>
  <header class="header">
    <div class="header-left">
      <span class="page-title">{{ pageTitle }}</span>
    </div>
    <div class="header-right">
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

defineEmits<{ command: [cmd: string] }>()

const route = useRoute()
const developerStore = useDeveloperStore()

const TITLES: Record<string, string> = {
  home: '首页',
  apps: '应用管理',
  docs: '开放接口',
  messages: '站内信',
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
  background: #fff;
  border-bottom: 1px solid #eef0f4;
}
.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
.user-entry {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #606266;
}
.user-avatar {
  background: #79bbff;
  color: #fff;
  font-size: 14px;
}
.user-name {
  font-size: 14px;
}
</style>
