<template>
  <el-container style="height: 100vh">
    <el-aside width="200px" style="background: #304156; position: relative">
      <div style="color: #fff; text-align: center; padding: 20px 0; font-size: 18px; font-weight: bold">
        汉江管理系统
      </div>
      <el-menu
        :default-active="$route.path"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
        router
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <span>首页</span>
        </el-menu-item>
        <el-menu-item index="/panel">
          <el-icon><DataAnalysis /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-sub-menu index="system">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统管理</span>
          </template>
          <el-menu-item index="/users"><el-icon><User /></el-icon><span>用户管理</span></el-menu-item>
          <el-menu-item index="/roles"><el-icon><UserFilled /></el-icon><span>角色管理</span></el-menu-item>
          <el-menu-item index="/permissions"><el-icon><Lock /></el-icon><span>权限管理</span></el-menu-item>
          <el-menu-item index="/audit"><el-icon><Document /></el-icon><span>审计日志</span></el-menu-item>
          <el-menu-item index="/audit/login"><el-icon><User /></el-icon><span>登录日志</span></el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="apis">
          <template #title>
            <el-icon><Link /></el-icon>
            <span>接口管理</span>
          </template>
          <el-menu-item index="/apis/swagger"><el-icon><Document /></el-icon><span>Swagger 文档</span></el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="open">
          <template #title>
            <el-icon><Connection /></el-icon>
            <span>开放平台</span>
          </template>
          <el-menu-item index="/apps"><el-icon><Grid /></el-icon><span>应用管理</span></el-menu-item>
        </el-sub-menu>
      </el-menu>

    </el-aside>
    <el-container>
      <el-header style="background: #fff; border-bottom: 1px solid #eee; display: flex; justify-content: flex-end; align-items: center">
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
      <el-main style="background: #f0f2f5">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

onMounted(() => {
  userStore.fetchUserInfo().catch(() => {})
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
