<template>
  <div>
    <!-- 关键指标卡片 -->
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="text-align: center">
            <div style="font-size: 32px; font-weight: 600; color: #409eff">{{ stats.userCount }}</div>
            <div style="color: #999; margin-top: 8px">用户总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="text-align: center">
            <div style="font-size: 32px; font-weight: 600; color: #67c23a">{{ stats.roleCount }}</div>
            <div style="color: #999; margin-top: 8px">角色总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="text-align: center">
            <div style="font-size: 32px; font-weight: 600; color: #e6a23c">{{ stats.appCount }}</div>
            <div style="color: #999; margin-top: 8px">开放应用数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="text-align: center">
            <div style="font-size: 32px; font-weight: 600; color: #f56c6c">{{ stats.todayLogin }}</div>
            <div style="color: #999; margin-top: 8px">今日登录</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 趋势图表 -->
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>近7天登录趋势</template>
          <v-chart :option="loginChartOption" style="height: 280px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>近7天操作日志趋势</template>
          <v-chart :option="auditChartOption" style="height: 280px" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>近30天新增用户趋势</template>
          <v-chart :option="newUsersChartOption" style="height: 280px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>近7天登录失败趋势</template>
          <v-chart :option="loginFailedChartOption" style="height: 280px" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 分布饼图 -->
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>用户角色分布</template>
          <v-chart :option="rolePieOption" style="height: 280px" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>用户状态分布</template>
          <v-chart :option="userStatusPieOption" style="height: 280px" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>通知渠道分布</template>
          <v-chart :option="channelPieOption" style="height: 280px" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 通知发送趋势 -->
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>近7天通知发送趋势（成功 vs 失败）</template>
          <v-chart :option="notifyChartOption" style="height: 280px" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 存储用量 -->
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>存储用量</template>
          <div style="display: flex; gap: 40px; align-items: center">
            <div>
              <div style="font-size: 28px; font-weight: 600; color: #409eff">{{ formatSize(storage.total_size_bytes) }}</div>
              <div style="color: #999; margin-top: 4px">总用量（{{ storage.total_count }} 个文件）</div>
            </div>
            <el-divider direction="vertical" style="height: 50px" />
            <div v-for="f in storage.by_folder" :key="f.folder" style="text-align: center">
              <div style="font-size: 20px; font-weight: 500">{{ formatSize(f.size_bytes) }}</div>
              <div style="color: #999; font-size: 12px; margin-top: 4px">{{ f.folder }}（{{ f.count }}）</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 系统监控 -->
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="24">
        <el-card v-if="canMonitor">
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

    <!-- 最近动态 -->
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>最近登录记录</span>
              <el-button text type="primary" size="small" @click="goAudit('login')">查看更多</el-button>
            </div>
          </template>
          <el-table :data="recentLogins" size="small" empty-text="暂无记录">
            <el-table-column label="用户" min-width="140" show-overflow-tooltip>
              <template #default="{ row }">{{ row.username }}{{ row.name ? '（' + row.name + '）' : '' }}</template>
            </el-table-column>
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
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>最近操作日志</span>
              <el-button text type="primary" size="small" @click="goAudit('audit')">查看更多</el-button>
            </div>
          </template>
          <el-table :data="recentAudits" size="small" empty-text="暂无记录">
            <el-table-column label="操作人" min-width="140" show-overflow-tooltip>
              <template #default="{ row }">{{ row.operator_username }}{{ row.operator_name ? '（' + row.operator_name + '）' : '' }}</template>
            </el-table-column>
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import request from '@/api/request'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'

use([CanvasRenderer, LineChart, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const router = useRouter()
const stats = ref({ userCount: 0, roleCount: 0, appCount: 0, todayLogin: 0 })
const loginTrend = ref({ dates: [] as string[], counts: [] as number[] })
const auditTrend = ref({ dates: [] as string[], counts: [] as number[] })
const roleDistribution = ref<any[]>([])
const userStatusDistribution = ref<any[]>([])
const channelDistribution = ref<any[]>([])
const newUsersTrend = ref({ dates: [] as string[], counts: [] as number[] })
const loginFailedTrend = ref({ dates: [] as string[], counts: [] as number[] })
const notifyTrend = ref({ dates: [] as string[], success: [] as number[], failed: [] as number[] })
const storage = ref({ total_size_bytes: 0, total_count: 0, by_folder: [] as any[] })
const recentLogins = ref<any[]>([])
const recentAudits = ref<any[]>([])

const loginChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: loginTrend.value.dates.map(d => d.slice(5)) },
  yAxis: { type: 'value', minInterval: 1 },
  series: [{ data: loginTrend.value.counts, type: 'line', smooth: true, areaStyle: {}, color: '#409eff' }],
}))

const auditChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: auditTrend.value.dates.map(d => d.slice(5)) },
  yAxis: { type: 'value', minInterval: 1 },
  series: [{ data: auditTrend.value.counts, type: 'bar', color: '#67c23a', barWidth: '40%' }],
}))

const newUsersChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: newUsersTrend.value.dates.map(d => d.slice(5)) },
  yAxis: { type: 'value', minInterval: 1 },
  series: [{ data: newUsersTrend.value.counts, type: 'bar', color: '#909399', barWidth: '60%' }],
}))

const loginFailedChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: loginFailedTrend.value.dates.map(d => d.slice(5)) },
  yAxis: { type: 'value', minInterval: 1 },
  series: [{ data: loginFailedTrend.value.counts, type: 'bar', color: '#f56c6c', barWidth: '40%' }],
}))

const rolePieOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { orient: 'vertical', right: 10, top: 'center' },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    center: ['40%', '50%'],
    label: { show: false },
    data: roleDistribution.value,
  }],
}))

const userStatusPieOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { orient: 'vertical', right: 10, top: 'center' },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    center: ['40%', '50%'],
    label: { show: false },
    data: userStatusDistribution.value,
    color: ['#67c23a', '#909399', '#e6a23c'],
  }],
}))

const channelPieOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { orient: 'vertical', right: 10, top: 'center' },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    center: ['40%', '50%'],
    label: { show: false },
    data: channelDistribution.value,
  }],
}))

const notifyChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['成功', '失败'], top: 0 },
  xAxis: { type: 'category', data: notifyTrend.value.dates.map(d => d.slice(5)) },
  yAxis: { type: 'value', minInterval: 1 },
  series: [
    { name: '成功', data: notifyTrend.value.success, type: 'bar', stack: 'total', color: '#67c23a', barWidth: '40%' },
    { name: '失败', data: notifyTrend.value.failed, type: 'bar', stack: 'total', color: '#f56c6c', barWidth: '40%' },
  ],
}))

const userStore = useUserStore()
const permissions = userStore.userInfo?.permissions || []
const canMonitor = computed(() => permissions.includes('*') || permissions.includes('notification:config'))
const monitor = ref<any>({})

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

function formatTime(t: string) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function goAudit(type: 'login' | 'audit') {
  router.push(type === 'login' ? '/audit/login' : '/audit')
}

function formatSize(bytes: number): string {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(1)} ${units[i]}`
}

onMounted(async () => {
  try {
    const res = await request.get('/dashboard/stats')
    const d = res.data
    stats.value = {
      userCount: d.cards.user_count,
      roleCount: d.cards.role_count,
      appCount: d.cards.app_count,
      todayLogin: d.cards.today_login,
    }
    loginTrend.value = d.login_trend
    auditTrend.value = d.audit_trend
    roleDistribution.value = d.role_distribution
    userStatusDistribution.value = d.user_status_distribution
    channelDistribution.value = d.notify_channel_distribution
    newUsersTrend.value = d.new_users_trend
    loginFailedTrend.value = d.login_failed_trend
    notifyTrend.value = d.notify_trend
    storage.value = d.storage_usage
    recentLogins.value = d.recent_logins
    recentAudits.value = d.recent_audits
  } catch (e) {
    console.error('dashboard load error', e)
  }
  if (canMonitor.value) {
    await fetchMonitor()
    monitorTimer = window.setInterval(fetchMonitor, 5000)
  }
})

onUnmounted(() => {
  if (monitorTimer) clearInterval(monitorTimer)
})
</script>
