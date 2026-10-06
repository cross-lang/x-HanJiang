<template>
  <div>
    <!-- 关键指标卡片 -->
    <el-row :gutter="20" class="hj-mb-20">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="hj-text-center">
            <div class="stat-value stat-blue">{{ stats.userCount }}</div>
            <div class="stat-label">用户总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="hj-text-center">
            <div class="stat-value stat-green">{{ stats.roleCount }}</div>
            <div class="stat-label">角色总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="hj-text-center">
            <div class="stat-value stat-orange">{{ stats.appCount }}</div>
            <div class="stat-label">开放应用数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="hj-text-center">
            <div class="stat-value stat-red">{{ stats.todayLogin }}</div>
            <div class="stat-label">今日登录</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 趋势图表 -->
    <el-row :gutter="20" class="hj-mb-20">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>近7天登录趋势</template>
          <v-chart :option="loginChartOption" class="hj-chart-box" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>近7天操作日志趋势</template>
          <v-chart :option="auditChartOption" class="hj-chart-box" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="hj-mb-20">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>近30天新增用户趋势</template>
          <v-chart :option="newUsersChartOption" class="hj-chart-box" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>近7天登录失败趋势</template>
          <v-chart :option="loginFailedChartOption" class="hj-chart-box" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 分布饼图 -->
    <el-row :gutter="20" class="hj-mb-20">
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>用户角色分布</template>
          <v-chart :option="rolePieOption" class="hj-chart-box" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>用户状态分布</template>
          <v-chart :option="userStatusPieOption" class="hj-chart-box" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>通知渠道分布</template>
          <v-chart :option="channelPieOption" class="hj-chart-box" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 通知发送趋势 -->
    <el-row :gutter="20" class="hj-mb-20">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>近7天通知发送趋势（成功 vs 失败）</template>
          <v-chart :option="notifyChartOption" class="hj-chart-box" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 开放平台统计 -->
    <el-row :gutter="20" class="hj-mb-20">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="hj-text-center">
            <div class="stat-value stat-blue">{{ openapi.cards.app_total }}</div>
            <div class="stat-label">开放应用总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="hj-text-center">
            <div class="stat-value stat-green">{{ openapi.cards.developer_count }}</div>
            <div class="stat-label">开发者总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="hj-text-center">
            <div class="stat-value stat-orange">{{ openapi.cards.pending_registrations }}</div>
            <div class="stat-label">待审批申请</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="hj-text-center">
            <div class="stat-value stat-red">{{ openapi.cards.week_registrations }}</div>
            <div class="stat-label">近7天申请</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="hj-mb-20">
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>开放应用状态分布</template>
          <v-chart :option="openAppStatusPieOption" class="hj-chart-box" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>应用申请审批状态分布</template>
          <v-chart :option="openRegStatusPieOption" class="hj-chart-box" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>近7天申请与审批趋势</template>
          <v-chart :option="openRegTrendOption" class="hj-chart-box" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="hj-mb-20">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>
            <div class="hj-flex-between">
              <span>最近应用申请</span>
              <el-button text type="primary" size="small" @click="goApprovals">查看全部</el-button>
            </div>
          </template>
          <el-table :data="recentRegistrations" size="small" empty-text="暂无申请记录">
            <el-table-column label="申请码" width="110">
              <template #default="{ row }">
                <code class="reg-code">{{ row.registration_code }}</code>
              </template>
            </el-table-column>
            <el-table-column prop="app_name" label="应用名称" min-width="140" show-overflow-tooltip />
            <el-table-column prop="registration_type" label="申请类型" width="110" />
            <el-table-column prop="status_label" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="regStatusType(row.status)" size="small">{{ row.status_label }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="owner_name" label="归属人" width="120" />
            <el-table-column prop="created_at" label="提交时间">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 存储用量 -->
    <el-row :gutter="20" class="hj-mb-20">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>存储用量</template>
          <div class="storage-wrap">
            <div>
              <div class="stat-value-lg stat-blue">{{ formatSize(storage.total_size_bytes) }}</div>
              <div class="stat-label-sm">总用量（{{ storage.total_count }} 个文件）</div>
            </div>
            <el-divider direction="vertical" class="storage-divider" />
            <div v-for="f in storage.by_folder" :key="f.folder" class="hj-text-center">
              <div class="stat-value-md">{{ formatSize(f.size_bytes) }}</div>
              <div class="stat-sub">{{ f.folder }}（{{ f.count }}）</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 系统监控 -->
    <el-row :gutter="20" class="hj-mb-20">
      <el-col :span="24">
        <el-card v-if="canMonitor">
          <template #header>
            <div class="hj-flex-between">
              <span>系统监控</span>
              <span class="hj-text-12 hj-text-gray">已运行 {{ monitor.uptime?.uptime_text || '-' }}</span>
            </div>
          </template>
          <el-row :gutter="20">
            <!-- CPU -->
            <el-col :xs="12" :sm="6">
              <div class="hj-text-center">
                <div class="stat-value stat-blue">{{ monitor.cpu?.percent ?? 0 }}%</div>
                <div class="stat-label">CPU 使用率</div>
                <div class="stat-sub">{{ monitor.cpu?.core_count }}核 / {{ monitor.cpu?.thread_count }}线程</div>
                <el-tag :type="statusType(monitor.cpu?.status)" size="small" class="stat-tag">
                  {{ statusText(monitor.cpu?.status) }}
                </el-tag>
              </div>
            </el-col>
            <!-- 内存 -->
            <el-col :xs="12" :sm="6">
              <div class="hj-text-center">
                <div class="stat-value stat-green">{{ monitor.memory?.percent ?? 0 }}%</div>
                <div class="stat-label">内存使用率</div>
                <div class="stat-sub">{{ monitor.memory?.used_gb }} / {{ monitor.memory?.total_gb }} GB</div>
                <el-tag :type="statusType(monitor.memory?.status)" size="small" class="stat-tag">
                  {{ statusText(monitor.memory?.status) }}
                </el-tag>
              </div>
            </el-col>
            <!-- 磁盘 -->
            <el-col :xs="12" :sm="6">
              <div class="hj-text-center">
                <div class="stat-value stat-orange">{{ monitor.disk?.used_percent ?? 0 }}%</div>
                <div class="stat-label">磁盘使用率</div>
                <div class="stat-sub">{{ monitor.disk?.used_gb }} / {{ monitor.disk?.total_gb }} GB</div>
                <el-tag :type="statusType(monitor.disk?.status)" size="small" class="stat-tag">
                  {{ statusText(monitor.disk?.status) }}
                </el-tag>
              </div>
            </el-col>
            <!-- 网络 -->
            <el-col :xs="12" :sm="6">
              <div class="hj-text-center">
                <div class="net-stat">
                  <span>↓ {{ monitor.network?.recv_kbps ?? 0 }} KB/s</span>
                  <span>↑ {{ monitor.network?.send_kbps ?? 0 }} KB/s</span>
                </div>
                <div class="stat-label">网络 IO</div>
                <div class="stat-sub">
                  收 {{ monitor.network?.bytes_recv_total_mb }} MB / 发 {{ monitor.network?.bytes_sent_total_mb }} MB
                </div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近动态 -->
    <el-row :gutter="20" class="hj-mb-20">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="hj-flex-between">
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
            <div class="hj-flex-between">
              <span>最近操作记录</span>
              <el-button text type="primary" size="small" @click="goAudit('audit')">查看更多</el-button>
            </div>
          </template>
          <el-table :data="recentAudits" size="small" empty-text="暂无记录">
            <el-table-column label="操作人" min-width="140" show-overflow-tooltip>
              <template #default="{ row }"
                >{{ row.operator_username }}{{ row.operator_name ? '（' + row.operator_name + '）' : '' }}</template
              >
            </el-table-column>
            <el-table-column label="实体" width="140">
              <template #default="{ row }">{{ formatAuditEntity(row.entity_type) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">{{ formatAuditAction(row.action) }}</template>
            </el-table-column>
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
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { formatMonthDayTime } from '@/utils/format'
import { formatAuditEntity, formatAuditAction } from '@/utils/audit-labels'
import { getDashboardStats, getNotificationMonitor } from '@/api/dashboard'
import type {
  DashboardStats,
  NameValueItem,
  NotificationMonitor,
  TrendSeries,
  NotifyTrend,
  StorageUsage,
  OpenapiStats,
} from '@/types/dashboard'

use([CanvasRenderer, LineChart, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const router = useRouter()
const stats = ref({ userCount: 0, roleCount: 0, appCount: 0, todayLogin: 0 })
const loginTrend = ref<TrendSeries>({ dates: [], counts: [] })
const auditTrend = ref<TrendSeries>({ dates: [], counts: [] })
const roleDistribution = ref<NameValueItem[]>([])
const userStatusDistribution = ref<NameValueItem[]>([])
const channelDistribution = ref<NameValueItem[]>([])
const newUsersTrend = ref<TrendSeries>({ dates: [], counts: [] })
const loginFailedTrend = ref<TrendSeries>({ dates: [], counts: [] })
const notifyTrend = ref<NotifyTrend>({ dates: [], success: [], failed: [] })
const storage = ref<StorageUsage>({ total_size_bytes: 0, total_count: 0, by_folder: [] })
const recentLogins = ref<DashboardStats['recent_logins']>([])
const recentAudits = ref<DashboardStats['recent_audits']>([])
const openapi = ref<OpenapiStats>({
  cards: { app_total: 0, developer_count: 0, pending_registrations: 0, week_registrations: 0 },
  app_status_distribution: [],
  registration_status_distribution: [],
  registration_trend: { dates: [], submitted: [], reviewed: [] },
  recent_registrations: [],
})
const recentRegistrations = computed(() => openapi.value.recent_registrations)

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
  series: [
    {
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['40%', '50%'],
      label: { show: false },
      data: roleDistribution.value,
    },
  ],
}))

const userStatusPieOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { orient: 'vertical', right: 10, top: 'center' },
  series: [
    {
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['40%', '50%'],
      label: { show: false },
      data: userStatusDistribution.value,
      color: ['#67c23a', '#909399', '#e6a23c'],
    },
  ],
}))

const channelPieOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { orient: 'vertical', right: 10, top: 'center' },
  series: [
    {
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['40%', '50%'],
      label: { show: false },
      data: channelDistribution.value,
    },
  ],
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

const openAppStatusPieOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { orient: 'vertical', right: 10, top: 'center' },
  series: [
    {
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['40%', '50%'],
      label: { show: false },
      data: openapi.value.app_status_distribution,
      color: ['#67c23a', '#f56c6c'],
    },
  ],
}))

const openRegStatusPieOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { orient: 'vertical', right: 10, top: 'center' },
  series: [
    {
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['40%', '50%'],
      label: { show: false },
      data: openapi.value.registration_status_distribution,
      color: ['#e6a23c', '#67c23a', '#f56c6c'],
    },
  ],
}))

const openRegTrendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['申请提交', '审批处理'], top: 0 },
  xAxis: { type: 'category', data: openapi.value.registration_trend.dates.map(d => d.slice(5)) },
  yAxis: { type: 'value', minInterval: 1 },
  series: [
    {
      name: '申请提交',
      data: openapi.value.registration_trend.submitted,
      type: 'bar',
      color: '#409eff',
      barWidth: '30%',
    },
    {
      name: '审批处理',
      data: openapi.value.registration_trend.reviewed,
      type: 'line',
      smooth: true,
      color: '#e6a23c',
    },
  ],
}))

/** 申请状态 → 表格状态标签类型 */
function regStatusType(status: string): 'warning' | 'success' | 'danger' {
  if (status === 'pending') return 'warning'
  if (status === 'approved') return 'success'
  return 'danger'
}

const userStore = useUserStore()
const permissions = userStore.userInfo?.permissions || []
const canMonitor = computed(() => permissions.includes('*') || permissions.includes('notification:config'))
const monitor = ref<NotificationMonitor>({ stats: { total: 0, success: 0, failed: 0, pending: 0 }, channels: [] })

function statusType(s: string | undefined) {
  if (s === 'critical') return 'danger'
  if (s === 'warning') return 'warning'
  return 'success'
}
function statusText(s: string | undefined) {
  if (s === 'critical') return '严重'
  if (s === 'warning') return '警告'
  return '正常'
}

let monitorTimer: number | undefined

async function fetchMonitor() {
  try {
    const res = await getNotificationMonitor()
    monitor.value = res.data
  } catch {
    // 普通用户可能没权限，忽略
  }
}

function formatTime(t: string | null | undefined): string {
  return formatMonthDayTime(t)
}

function goAudit(type: 'login' | 'audit') {
  router.push(type === 'login' ? '/logs/login' : '/logs/audit')
}

/** 跳转应用审批页查看全部申请 */
function goApprovals() {
  router.push('/app-approvals')
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
    const res = await getDashboardStats()
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
    openapi.value = d.openapi
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

<style scoped>
/* 指标卡片 */
.stat-value {
  font-size: 32px;
  font-weight: 600;
}
.stat-value-lg {
  font-size: 28px;
  font-weight: 600;
}
.stat-value-md {
  font-size: 20px;
  font-weight: 500;
}
.stat-blue {
  color: #409eff;
}
.stat-green {
  color: #67c23a;
}
.stat-orange {
  color: #e6a23c;
}
.stat-red {
  color: #f56c6c;
}
.stat-label {
  color: #999;
  margin-top: 8px;
}
.stat-label-sm {
  color: #999;
  margin-top: 4px;
}
.stat-sub {
  font-size: 12px;
  color: #999;
}
.stat-tag {
  margin-top: 6px;
}

/* 存储用量 */
.storage-wrap {
  display: flex;
  gap: 40px;
  align-items: center;
}
.storage-divider {
  height: 50px;
}

/* 网络 IO */
.net-stat {
  display: flex;
  justify-content: center;
  gap: 16px;
  font-size: 18px;
  font-weight: bold;
  color: #909399;
}
.reg-code {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 12.5px;
  color: #409eff;
  background: #ecf5ff;
  padding: 1px 6px;
  border-radius: 4px;
}
</style>
