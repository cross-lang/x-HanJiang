<template>
  <el-header class="header-bar">
    <Search />
    <NotificationBell />
    <el-tooltip content="我是小江，您的 AI 助手" placement="bottom" effect="light" :show-after="200">
      <div class="ai-btn" @click="emit('open-ai')">
        <div class="ai-entry">
          <el-icon :size="18"><MagicStick /></el-icon>
          <span>小江</span>
        </div>
      </div>
    </el-tooltip>
    <el-dropdown @command="cmd => emit('command', cmd)">
      <span class="user-trigger">
        <el-avatar :size="36" class="user-avatar">
          {{ (userStore.userInfo?.name || userStore.userInfo?.username || 'U').charAt(0) }}
        </el-avatar>
        <div class="user-info">
          <div class="user-name">{{ userStore.userInfo?.name || userStore.userInfo?.username || '用户' }}</div>
          <div class="user-email">{{ userStore.userInfo?.email || '' }}</div>
        </div>
        <el-icon><ArrowDown /></el-icon>
      </span>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="profile"
            ><el-icon class="menu-icon"><User /></el-icon>个人中心</el-dropdown-item
          >
          <el-dropdown-item divided command="logout"
            ><el-icon class="menu-icon"><SwitchButton /></el-icon>退出登录</el-dropdown-item
          >
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </el-header>
</template>

<script setup lang="ts">
import { useUserStore } from '@/stores/user'
import Search from '@/components/Search.vue'
import NotificationBell from '@/components/NotificationBell.vue'

const emit = defineEmits<{ 'open-ai': []; command: [cmd: string] }>()

const userStore = useUserStore()
</script>

<style scoped>
.header-bar {
  background: #fff;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  user-select: none;
  -webkit-user-select: none;
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
.user-trigger {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
}
.user-avatar {
  background: #79bbff;
}
.user-info {
  line-height: 1.4;
}
.user-name {
  font-weight: 500;
  color: #333;
}
.user-email {
  font-size: 12px;
  color: #999;
}
.menu-icon {
  margin-right: 8px;
}
</style>
