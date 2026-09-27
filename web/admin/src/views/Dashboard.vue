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
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="6" v-for="item in quickLinks" :key="item.path">
        <el-card shadow="hover" style="cursor: pointer" @click="$router.push(item.path)">
          <div style="display: flex; align-items: center; gap: 16px">
            <div :style="{
              width: '48px', height: '48px', borderRadius: '8px',
              background: item.color, display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#fff', fontSize: '24px',
            }">
              <el-icon><component :is="item.icon" /></el-icon>
            </div>
            <div>
              <div style="font-weight: 500; font-size: 15px">{{ item.title }}</div>
              <div style="color: #999; font-size: 12px; margin-top: 4px">{{ item.desc }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 我的最近动态 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>我的最近登录</span>
              <el-button text type="primary" size="small" @click="$router.push('/audit/login?mine=true')">查看全部</el-button>
            </div>
          </template>
          <el-table :data="myLogins" size="small" empty-text="暂无记录">
            <el-table-column prop="ip_address" label="IP" width="120" />
            <el-table-column prop="status" label="状态" width="70">
              <template #default="{ row }">
                <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
                  {{ row.status === 'success' ? '成功' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div style="justify-content: space-between; align-items: center; display: flex">
              <span>我的最近操作</span>
              <el-button text type="primary" size="small" @click="$router.push('/audit?mine=true')">查看全部</el-button>
            </div>
          </template>
          <el-table :data="myAudits" size="small" empty-text="暂无记录">
            <el-table-column prop="entity_type" label="实体" width="100" />
            <el-table-column prop="action" label="操作" width="80" />
            <el-table-column prop="ip_address" label="IP" width="120" />
            <el-table-column prop="created_at" label="时间">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import request from '@/api/request'

const userStore = useUserStore()
const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })

const quickLinks = [
  { title: '用户管理', desc: '查看和管理系统用户', path: '/users', icon: 'User', color: '#409eff' },
  { title: '角色管理', desc: '分配角色和权限', path: '/roles', icon: 'UserFilled', color: '#67c23a' },
  { title: '开放应用', desc: '管理第三方接入应用', path: '/apps', icon: 'Grid', color: '#e6a23c' },
  { title: '个人中心', desc: '修改个人信息和密码', path: '/profile', icon: 'Setting', color: '#909399' },
]

const myLogins = ref<any[]>([])
const myAudits = ref<any[]>([])

function formatTime(t: string) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(async () => {
  try {
    const res = await request.get('/dashboard/my-activity')
    myLogins.value = res.data.recent_logins
    myAudits.value = res.data.recent_audits
  } catch (e) {
    // 静默处理
  }
})
</script>
