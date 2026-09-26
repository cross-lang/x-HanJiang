<template>
  <div>
    <!-- 欢迎信息 -->
    <el-card style="margin-bottom: 20px">
      <div style="display: flex; justify-content: space-between; align-items: center">
        <div>
          <div style="font-size: 20px; font-weight: 500">
            欢迎回来，{{ userStore.userInfo?.name || userStore.userInfo?.username }}
          </div>
          <div style="color: #999; margin-top: 5px">今天是 {{ today }}</div>
        </div>
      </div>
    </el-card>

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

    <!-- 图表区 -->
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>近7天登录趋势</template>
          <v-chart :option="loginChartOption" style="height: 300px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>近7天操作日志趋势</template>
          <v-chart :option="auditChartOption" style="height: 300px" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>用户角色分布</template>
          <v-chart :option="rolePieOption" style="height: 300px" />
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card shadow="hover">
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
      </el-col>
    </el-row>

    <!-- 最近动态 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>最近登录记录</template>
          <el-table :data="recentLogins" size="small" empty-text="暂无记录">
            <el-table-column prop="username" label="用户" width="120" />
            <el-table-column prop="ip_address" label="IP" width="130" />
            <el-table-column prop="status" label="状态" width="80">
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
          <template #header>最近操作日志</template>
          <el-table :data="recentAudits" size="small" empty-text="暂无记录">
            <el-table-column prop="operator_name" label="操作人" width="100" />
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
import { ref, computed, onMounted } from 'vue'
import request from '@/api/request'
import { useUserStore } from '@/stores/user'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'

use([CanvasRenderer, LineChart, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])

const userStore = useUserStore()
const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })

const stats = ref({ userCount: 0, roleCount: 0, appCount: 0, todayLogin: 0 })
const loginTrend = ref({ dates: [] as string[], counts: [] as number[] })
const auditTrend = ref({ dates: [] as string[], counts: [] as number[] })
const roleDistribution = ref<any[]>([])
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

function formatTime(t: string) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
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
    recentLogins.value = d.recent_logins
    recentAudits.value = d.recent_audits
  } catch (e) {
    console.error('dashboard load error', e)
  }
})
</script>
