<template>
  <el-card>
    <div
      style="
        margin-bottom: 16px;
        text-align: right;
        display: flex;
        justify-content: flex-end;
        align-items: center;
        gap: 8px;
      "
    >
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
            <el-button size="small" link @click="showDetail(row as LoginLogItem)">详情</el-button>
          </template>
        </el-table-column>
      </template>
      <template v-else>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column label="操作人" min-width="160" show-overflow-tooltip>
          <template #default="{ row }"
            >{{ row.operator_username
            }}{{ row.operator_real_name ? '（' + row.operator_real_name + '）' : '' }}</template
          >
        </el-table-column>
        <el-table-column prop="entity_type" label="实体类型" min-width="120" />
        <el-table-column prop="action" label="操作" min-width="120" />
        <el-table-column prop="remarks" label="备注" min-width="200" show-overflow-tooltip />
        <el-table-column prop="ip_address" label="IP" min-width="140" />
        <el-table-column prop="created_at" label="时间" min-width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button size="small" link @click="showDetail(row as AuditLogItem)">详情</el-button>
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
    <el-dialog v-model="detailVisible" :title="isLoginLog ? '登录详情' : '审计详情'" width="700px">
      <div v-if="detailRow">
        <template v-if="loginDetail">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="操作者"
              >{{ loginDetail.username }}（{{ loginDetail.name || '-' }}）</el-descriptions-item
            >
            <el-descriptions-item label="操作时间">{{ loginDetail.created_at }}</el-descriptions-item>
            <el-descriptions-item label="登录方式">{{ loginDetail.login_type }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="loginDetail.status === 'success' ? 'success' : 'danger'">
                {{ loginStatusText(loginDetail.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="IP">{{ loginDetail.ip_address }}</el-descriptions-item>
            <el-descriptions-item label="用户ID">{{ loginDetail.user_id ?? '-' }}</el-descriptions-item>
          </el-descriptions>
        </template>
        <template v-else-if="auditDetail">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="操作者"
              >{{ auditDetail.operator_username }}（{{ auditDetail.operator_real_name || '-' }}）</el-descriptions-item
            >
            <el-descriptions-item label="操作时间">{{ auditDetail.created_at }}</el-descriptions-item>
            <el-descriptions-item label="实体类型">{{ auditDetail.entity_type }}</el-descriptions-item>
            <el-descriptions-item label="操作">{{ auditDetail.action }}</el-descriptions-item>
            <el-descriptions-item label="IP">{{ auditDetail.ip_address }}</el-descriptions-item>
            <el-descriptions-item label="备注">{{ auditDetail.remarks }}</el-descriptions-item>
          </el-descriptions>
          <el-divider />
          <h4>变更前数据</h4>
          <pre style="background: #f5f5f5; padding: 12px; border-radius: 4px; font-size: 12px; overflow: auto">{{
            JSON.stringify(auditDetail.before_data, null, 2)
          }}</pre>
          <h4>变更后数据</h4>
          <pre style="background: #f5f5f5; padding: 12px; border-radius: 4px; font-size: 12px; overflow: auto">{{
            JSON.stringify(auditDetail.after_data, null, 2)
          }}</pre>
        </template>
      </div>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { formatDateTime } from '@/utils/format'
import { downloadResponseBlob } from '@/utils/download'
import {
  listAuditLogs,
  listLoginLogs,
  getAuditLogDetail,
  getLoginLogDetail,
  exportAuditCsv,
  exportLoginLogCsv,
} from '@/api/audit'
import type { AuditLogItem, LoginLogItem } from '@/types/audit'

const route = useRoute()
const userStore = useUserStore()
const props = defineProps<{ logType?: string }>()
const isLoginLog = computed(() => props.logType === 'login')
const searchPlaceholder = computed(() => (isLoginLog.value ? '按IP/状态/登录方式搜索' : '按操作人/IP/备注搜索'))

const list = ref<(AuditLogItem | LoginLogItem)[]>([])
const detailVisible = ref(false)
const detailRow = ref<AuditLogItem | LoginLogItem | null>(null)
const loading = ref(false)

/** 详情弹窗按当前类型收窄为具体结构 */
const loginDetail = computed<LoginLogItem | null>(() =>
  isLoginLog.value ? (detailRow.value as LoginLogItem | null) : null,
)
const auditDetail = computed<AuditLogItem | null>(() =>
  isLoginLog.value ? null : (detailRow.value as AuditLogItem | null),
)

async function showDetail(row: AuditLogItem | LoginLogItem) {
  try {
    const res = isLoginLog.value ? await getLoginLogDetail(row.id) : await getAuditLogDetail(row.id)
    detailRow.value = res.data
    detailVisible.value = true
  } catch {
    // 错误已处理
  }
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
    const base = {
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value.trim() || undefined,
    }
    const myId = userStore.userInfo?.id
    if (isLoginLog.value) {
      const res = await listLoginLogs(isMine.value && myId ? { ...base, user_id: myId } : base)
      list.value = res.data.items
      total.value = res.data.total
    } else {
      const res = await listAuditLogs(isMine.value && myId ? { ...base, operator_id: myId } : base)
      list.value = res.data.items
      total.value = res.data.total
    }
  } catch {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  fetchList()
}

async function handleExport() {
  try {
    const params = { keyword: keyword.value.trim() || undefined }
    const resp = isLoginLog.value ? await exportLoginLogCsv(params) : await exportAuditCsv(params)
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      ElMessage.error(err.message || `导出失败（${resp.status}）`)
      return
    }
    await downloadResponseBlob(resp, isLoginLog.value ? 'login_logs_export.csv' : 'audit_logs_export.csv')
  } catch {
    ElMessage.error('导出失败，请稍后重试')
  }
}

onMounted(() => {
  fetchList()
})

watch(
  () => props.logType,
  () => {
    page.value = 1
    fetchList()
  },
)
</script>
