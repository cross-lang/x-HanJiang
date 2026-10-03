<template>
  <aside class="sidebar" :class="{ collapsed }">
    <div class="brand" @click="router.push('/home')">
      <el-icon class="brand-icon" :size="22"><Connection /></el-icon>
      <span v-show="!collapsed" class="brand-text">汉江开放平台</span>
    </div>

    <el-menu :default-active="activePath" router class="side-menu" :collapse="collapsed">
      <el-menu-item index="/home">
        <el-icon><HomeFilled /></el-icon>
        <template #title>首页</template>
      </el-menu-item>
      <el-menu-item index="/apps">
        <el-icon><Grid /></el-icon>
        <template #title>应用管理</template>
      </el-menu-item>
      <el-menu-item index="/docs">
        <el-icon><Document /></el-icon>
        <template #title>开放接口</template>
      </el-menu-item>
      <el-menu-item index="/profile">
        <el-icon><User /></el-icon>
        <template #title>个人中心</template>
      </el-menu-item>
    </el-menu>

    <div class="collapse-btn" @click="$emit('toggle')">
      <el-icon :size="16"><Fold /></el-icon>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { HomeFilled } from '@element-plus/icons-vue'

defineProps<{ collapsed: boolean }>()
defineEmits<{ toggle: [] }>()

const route = useRoute()
const router = useRouter()

// 侧边栏按一级路由高亮
const activePath = computed(() => `/${route.path.split('/')[1] || 'home'}`)
</script>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  width: 220px;
  background: #fff;
  border-right: 1px solid #eef0f4;
  transition: width 0.2s;
}
.sidebar.collapsed {
  width: 64px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 56px;
  padding: 0 16px;
  cursor: pointer;
  border-bottom: 1px solid #f0f2f5;
}
.brand-icon {
  color: #409eff;
  flex-shrink: 0;
}
.brand-text {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
}
.side-menu {
  flex: 1;
  border-right: none;
}
.collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 44px;
  border-top: 1px solid #f0f2f5;
  color: #909399;
  cursor: pointer;
  transition: color 0.2s;
}
.collapse-btn:hover {
  color: #409eff;
}
</style>
