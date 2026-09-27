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

    <!-- 系统监控 -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>系统监控</span>
              <span style="font-size: 12px; color: #999">已运行 {{ monitor.uptime?.uptime_text || '-' }}</span>
            </div>
          </template>
          <el-row :gutter="20">
            <!-- CPU -->
            <el-col :xs="12" :sm="6">
              <div style="text-align: center">
                <div style="font-size: 28px; font-weight: bold; color: #409eff">
                  {{ monitor.cpu?.percent ?? 0 }}%
                </div>
                <div style="color: #999; margin: 8px 0">CPU 使用率</div>
                <div style="font-size: 12px; color: #999">
                  {{ monitor.cpu?.core_count }}核 / {{ monitor.cpu?.thread_count }}线程
                </div>
                <el-tag :type="statusType(monitor.cpu?.status)" size="small" style="margin-top: 6px">
                  {{ statusText(monitor.cpu?.status) }}
                </el-tag>
              </div>
            </el-col>
            <!-- 内存 -->
            <el-col :xs="12" :sm="6">
              <div style="text-align: center">
                <div style="font-size: 28px; font-weight: bold; color: #67c23a">
                  {{ monitor.memory?.percent ?? 0 }}%
                </div>
                <div style="color: #999; margin: 8px 0">内存使用率</div>
                <div style="font-size: 12px; color: #999">
                  {{ monitor.memory?.used_gb }} / {{ monitor.memory?.total_gb }} GB
                </div>
                <el-tag :type="statusType(monitor.memory?.status)" size="small" style="margin-top: 6px">
                  {{ statusText(monitor.memory?.status) }}
                </el-tag>
              </div>
            </el-col>
            <!-- 磁盘 -->
            <el-col :xs="12" :sm="6">
              <div style="text-align: center">
                <div style="font-size: 28px; font-weight: bold; color: #e6a23c">
                  {{ monitor.disk?.used_percent ?? 0 }}%
                </div>
                <div style="color: #999; margin: 8px 0">磁盘使用率</div>
                <div style="font-size: 12px; color: #999">
                  {{ monitor.disk?.used_gb }} / {{ monitor.disk?.total_gb }} GB
                </div>
                <el-tag :type="statusType(monitor.disk?.status)" size="small" style="margin-top: 6px">
                  {{ statusText(monitor.disk?.status) }}
                </el-tag>
              </div>
            </el-col>
            <!-- 网络 -->
            <el-col :xs="12" :sm="6">
              <div style="text-align: center">
                <div style="display: flex; justify-content: center; gap: 16px; font-size: 18px; font-weight: bold; color: #909399">
                  <span>↓ {{ monitor.network?.recv_kbps ?? 0 }} KB/s</span>
                  <span>↑ {{ monitor.network?.send_kbps ?? 0 }} KB/s</span>
                </div>
                <div style="color: #999; margin: 8px 0">网络 IO</div>
                <div style="font-size: 12px; color: #999">
                  收 {{ monitor.network?.bytes_recv_total_mb }} MB / 发 {{ monitor.network?.bytes_sent_total_mb }} MB
                </div>
              </div>
            </el-col>
          </el-row>
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
import { ref, onMounted, onUnmounted } from 'vue'
import { useUserStore } from '@/stores/user'
import request from '@/api/request'

const userStore = useUserStore()
const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })

const allQuickLinks = [
  { title: '用户管理', desc: '查看和管理系统用户', path: '/users', icon: 'User', color: '#409eff', perm: 'user:view' },
  { title: '角色管理', desc: '分配角色和权限', path: '/roles', icon: 'UserFilled', color: '#67c23a', perm: 'role:view' },
  { title: '开放应用', desc: '管理第三方接入应用', path: '/apps', icon: 'Grid', color: '#e6a23c', perm: 'openapi_app:view' },
  { title: '个人中心', desc: '修改个人信息和密码', path: '/profile', icon: 'Setting', color: '#909399', perm: '' },
]

const permissions = userStore.userInfo?.permissions || []
const quickLinks = allQuickLinks.filter(l => !l.perm || permissions.includes('*') || permissions.includes(l.perm))

const myLogins = ref<any[]>([])
const myAudits = ref<any[]>([])
const monitor = ref<any>({})

function formatTime(t: string) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function statusType(s: string) {
  if (s === 'critical') return 'danger'
  if (s === 'warning') return 'warning'
  return 'success'
}
function statusText(s: string) {
  if (s === 'critical') return '严重'
  if (s === 'warning') return '警告'
  return '正常'
}

let monitorTimer: number | undefined

async function fetchMonitor() {
  try {
    const res = await request.get('/admin/notification-configs/monitor/system')
    monitor.value = res.data
  } catch (e) {
    // 普通用户可能没权限，忽略
  }
}

onMounted(async () => {
  try {
    const res = await request.get('/dashboard/my-activity')
    myLogins.value = res.data.recent_logins
    myAudits.value = res.data.recent_audits
  } catch (e) {
    // 静默处理
  }
  await fetchMonitor()
  monitorTimer = window.setInterval(fetchMonitor, 5000)
})

onUnmounted(() => {
  if (monitorTimer) clearInterval(monitorTimer)
})
</script>
