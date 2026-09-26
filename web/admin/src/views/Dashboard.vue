<template>
  <div>
    <!-- 欢迎信息 -->
    <el-card>
      <div style="display: flex; justify-content: space-between; align-items: center">
        <div>
          <div style="font-size: 20px; font-weight: 500">
            欢迎回来，{{ userStore.userInfo?.name || userStore.userInfo?.username }}
          </div>
          <div style="color: #999; margin-top: 5px">今天是 {{ today }}</div>
        </div>
      </div>
    </el-card>

    <!-- 快捷入口 -->
    <el-card style="margin-top: 20px">
      <template #header>快捷入口</template>
      <el-space wrap>
        <el-button type="primary" @click="$router.push('/users')">用户管理</el-button>
        <el-button type="success" @click="$router.push('/roles')">角色管理</el-button>
        <el-button type="warning" @click="$router.push('/permissions')">权限管理</el-button>
        <el-button type="danger" @click="$router.push('/audit')">审计日志</el-button>
        <el-button type="warning" plain @click="$router.push('/audit/login')">登录日志</el-button>
        <el-button type="info" @click="$router.push('/apps')">开放应用</el-button>
        <el-button @click="$router.push('/profile')">个人中心</el-button>
      </el-space>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })
</script>
