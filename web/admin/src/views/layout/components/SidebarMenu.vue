<template>
  <el-aside :width="collapsed ? '64px' : '200px'" class="sidebar" :class="{ 'is-collapsed': collapsed }">
    <div class="app-title" :title="collapsed ? '点击展开菜单' : '点击收起菜单'" @click="emit('toggle')">
      <img src="/logo-icon.png" class="app-logo" alt="汉江管理系统" />
      <span v-if="!collapsed" class="app-name">汉江管理系统</span>
    </div>
    <el-menu
      :default-active="$route.path"
      background-color="#ffffff"
      text-color="#5a5e66"
      active-text-color="#409eff"
      router
      :collapse="collapsed"
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
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useUserStore } from '@/stores/user'

defineProps<{ collapsed: boolean }>()
const emit = defineEmits<{ toggle: [] }>()

const userStore = useUserStore()

const menus = computed(() => userStore.menus)
</script>

<style scoped>
.sidebar {
  background: #ffffff;
  border-right: 1px solid #e4e7ed;
  position: relative;
  transition: width 0.25s ease;
  overflow: hidden;
}
.app-title {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #303133;
  padding: 16px 0;
  font-size: 18px;
  font-weight: bold;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  transition:
    color 0.2s ease,
    background-color 0.2s ease;
}
.app-title:hover {
  color: #409eff;
  background-color: #f5f7fa;
}
.app-logo {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  flex-shrink: 0;
  transition:
    width 0.25s ease,
    height 0.25s ease;
}
.is-collapsed .app-logo {
  width: 32px;
  height: 32px;
}
.app-name {
  line-height: 1;
}
</style>
