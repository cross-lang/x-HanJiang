<template>
  <el-card>
    <div style="margin-bottom: 16px; text-align: right; display: flex; justify-content: flex-end; align-items: center; gap: 8px">
      <el-input
        v-model="keyword"
        :placeholder="searchPlaceholder"
        style="width: 230px"
        clearable
        @keyup.enter="handleSearch"
        @clear="handleSearch"
      />
      <el-button type="primary" icon="Search" @click="handleSearch">搜索</el-button>
      <el-button icon="Download" @click="handleExport">导出CSV</el-button>
    </div>
    <el-table :data="list" v-loading="loading">
      <template v-if="isLoginLog">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="name" label="姓名" min-width="120" />
        <el-table-column prop="login_type" label="登录方式" min-width="120" />
        <el-table-column prop="status" label="状态" min-width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'">{{ loginStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP" min-width="140" />
        <el-table-column prop="created_at" label="时间" min-width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button size="small" link @click="showDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </template>
      <template v-else>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="operator_username" label="用户名" min-width="120" />
        <el-table-column prop="operator_real_name" label="姓名" min-width="120" />
        <el-table-column prop="entity_type" label="实体类型" min-width="120" />
        <el-table-column prop="action" label="操作" min-width="120" />
        <el-table-column prop="remarks" label="备注" min-width="200" show-overflow-tooltip />
        <el-table-column prop="ip_address" label="IP" min-width="140" />
        <el-table-column prop="created_at" label="时间" min-width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button size="small" link @click="showDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </template>
    </el-table>
    <el-pagination
      style="margin-top: 20px; justify-content: flex-end; display: flex"
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      @current-change="fetchList"
    />
    <el-dialog v-model="detailVisible" title="审计详情" width="700px">
      <div v-if="detailRow">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="操作者">{{ detailRow.operator_name }}</el-descriptions-item>
          <el-descriptions-item label="操作时间">{{ detailRow.created_at }}</el-descriptions-item>
          <el-descriptions-item label="实体类型">{{ detailRow.entity_type }}</el-descriptions-item>
          <el-descriptions-item label="操作">{{ detailRow.action }}</el-descriptions-item>
          <el-descriptions-item label="IP">{{ detailRow.ip_address }}</el-descriptions-item>
          <el-descriptions-item label="备注">{{ detailRow.remarks }}</el-descriptions-item>
        </el-descriptions>
        <el-divider />
        <h4>变更前数据</h4>
        <pre style="background: #f5f5f5; padding: 12px; border-radius: 4px; font-size: 12px; overflow: auto">{{ JSON.stringify(detailRow.before_data, null, 2) }}</pre>
        <h4>变更后数据</h4>
        <pre style="background: #f5f5f5; padding: 12px; border-radius: 4px; font-size: 12px; overflow: auto">{{ JSON.stringify(detailRow.after_data, null, 2) }}</pre>
      </div>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '@/api/request'
import { useUserStore } from '@/stores/user'
import { formatDateTime } from '@/utils/format'

const route = useRoute()
const userStore = useUserStore()
const props = defineProps<{ logType?: string }>()
const isLoginLog = computed(() => props.logType === 'login')
const searchPlaceholder = computed(() =>
  isLoginLog.value ? '按IP/状态/登录方式搜索' : '按操作人/IP/备注搜索'
)

const list = ref<any[]>([])
const detailVisible = ref(false)
const detailRow = ref<any>(null)
const loading = ref(false)

function showDetail(row: any) {
  detailRow.value = row
  detailVisible.value = true
}
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const keyword = ref('')

// 登录状态：英文原值 → 中文展示（仅前端维护，后端值不变）
const loginStatusText = (s: string) => (s === 'success' ? '成功' : '失败')

// 从首页跳转时带 mine=true，只看自己的记录
const isMine = computed(() => route.query.mine === 'true')

async function fetchList() {
  loading.value = true
  try {
    const url = isLoginLog.value ? '/audit/login-logs' : '/audit/logs'
    const params: any = {
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value.trim() || undefined,
    }
    if (isMine.value) {
      const myId = userStore.userInfo?.id
      if (myId) {
        if (isLoginLog.value) {
          params.user_id = myId
        } else {
          params.operator_id = myId
        }
      }
    }
    const res = await request.get(url, { params })
    list.value = res.data.items
    total.value = res.data.total
  } catch (e) {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  fetchList()
}

function handleExport() {
  const token = localStorage.getItem('access_token') || ''
  const isLogin = isLoginLog.value
  const api = isLogin ? '/api/v1/audit/login-logs/export' : '/api/v1/audit/logs/export'
  const filename = isLogin ? 'login_logs_export.csv' : 'audit_logs_export.csv'
  fetch(api, { headers: { Authorization: `Bearer ${token}` } })
    .then(async r => {
      if (!r.ok) {
        const err = await r.json().catch(() => ({}))
        ElMessage.error(err.message || `导出失败（${r.status}）`)
        return
      }
      return r.blob()
    })
    .then(blob => {
      if (!blob) return
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      URL.revokeObjectURL(url)
    })
}

onMounted(() => {
  fetchList()
})

watch(() => props.logType, () => {
  page.value = 1
  fetchList()
})
</script>
