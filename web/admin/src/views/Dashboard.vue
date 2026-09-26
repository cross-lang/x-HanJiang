<template>
  <div>
    <!-- 欢迎信息 -->
    <el-card style="margin-bottom: 20px">
      <div style="display: flex; justify-content: space-between; align-items: center">
        <div>
          <div style="font-size: 20px; font-weight: 500">
            欢迎回来，{{ userStore.userInfo?.name || userStore.userInfo?.username }}
          </div>
          <div style="color: #999; margin-top: 5px">
            今天是 {{ today }}
          </div>
        </div>
        <div style="text-align: right; color: #999; font-size: 13px">
          <div>{{ userStore.userInfo?.email }}</div>
          <div style="margin-top: 4px">{{ userStore.userInfo?.phone || '' }}</div>
        </div>
      </div>
    </el-card>

    <!-- 关键指标卡片 -->
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="6">
        <el-card>
          <div style="text-align: center">
            <div style="font-size: 28px; color: #409eff">{{ stats.userCount }}</div>
            <div style="color: #999; margin-top: 8px">用户总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div style="text-align: center">
            <div style="font-size: 28px; color: #67c23a">{{ stats.roleCount }}</div>
            <div style="color: #999; margin-top: 8px">角色总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div style="text-align: center">
            <div style="font-size: 28px; color: #e6a23c">{{ stats.appCount }}</div>
            <div style="color: #999; margin-top: 8px">开放应用数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div style="text-align: center">
            <div style="font-size: 28px; color: #f56c6c">{{ stats.todayLogins }}</div>
            <div style="color: #999; margin-top: 8px">今日登录</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快捷入口 -->
    <el-card style="margin-bottom: 20px">
      <template #header>快捷入口</template>
      <el-space wrap>
        <el-button type="primary" @click="$router.push('/users')">用户管理</el-button>
        <el-button type="success" @click="$router.push('/roles')">角色管理</el-button>
        <el-button type="warning" @click="$router.push('/permissions')">权限管理</el-button>
        <el-button type="danger" @click="$router.push('/audit')">审计日志</el-button>
        <el-button type="info" @click="$router.push('/apps')">开放应用</el-button>
        <el-button @click="$router.push('/profile')">个人中心</el-button>
      </el-space>
    </el-card>

    <!-- 最近动态 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card>
          <template #header>最近登录记录</template>
          <el-table :data="recentLogins" size="small" empty-text="暂无记录">
            <el-table-column prop="operator_name" label="用户" />
            <el-table-column prop="ip" label="IP" width="120" />
            <el-table-column prop="created_at" label="时间" width="180">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>最近操作日志</template>
          <el-table :data="recentActions" size="small" empty-text="暂无记录">
            <el-table-column prop="operator_name" label="操作人" width="100" />
            <el-table-column prop="path" label="路径" show-overflow-tooltip />
            <el-table-column prop="status_code" label="状态" width="70" />
            <el-table-column prop="created_at" label="时间" width="160">
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
import request from '@/api/request'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })

const stats = ref({ userCount: 0, roleCount: 0, appCount: 0, todayLogins: 0 })
const recentLogins = ref<any[]>([])
const recentActions = ref<any[]>([])

function formatTime(t: string) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(async () => {
  try {
    const [users, roles, apps, logins, actions] = await Promise.all([
      request.get('/users', { params: { page: 1, page_size: 1 } }),
      request.get('/roles', { params: { page: 1, page_size: 1 } }),
      request.get('/admin/apps', { params: { page: 1, page_size: 1 } }),
      request.get('/audit/login-logs', { params: { page: 1, page_size: 5 } }),
      request.get('/audit/logs', { params: { page: 1, page_size: 5 } }),
    ])
    stats.value.userCount = users.data?.total || 0
    stats.value.roleCount = roles.data?.total || 0
    stats.value.appCount = apps.data?.total || 0
    recentLogins.value = logins.data?.items || logins.data?.list || []
    recentActions.value = actions.data?.items || actions.data?.list || []
    // 今日登录数：从登录记录里筛今天的
    const todayStr = new Date().toDateString()
    stats.value.todayLogins = recentLogins.value.filter((l: any) => new Date(l.created_at).toDateString() === todayStr).length
  } catch (e) {
    console.error('dashboard load error', e)
  }
})
</script>
