<template>
  <el-card>
    <div class="hj-toolbar">
      <div class="hj-flex hj-gap-8">
        <el-select v-model="typeFilter" placeholder="申请类型" clearable style="width: 130px" @change="handleFilter">
          <el-option label="创建申请" value="create" />
          <el-option label="修改申请" value="update" />
        </el-select>
        <el-select v-model="statusFilter" placeholder="审批状态" clearable style="width: 130px" @change="handleFilter">
          <el-option label="待审批" value="pending" />
          <el-option label="已通过" value="approved" />
          <el-option label="已驳回" value="rejected" />
        </el-select>
        <el-input
          v-model="keyword"
          placeholder="按 App ID/应用名搜索"
          style="width: 230px"
          clearable
          @keyup.enter="handleFilter"
          @clear="handleFilter"
        />
        <el-button type="primary" icon="Search" @click="handleFilter">搜索</el-button>
      </div>
    </div>
    <el-table :data="list" v-loading="loading">
      <el-table-column label="申请码" width="90">
        <template #default="{ row }">
          <span class="reg-id-text">{{ row.registration_code || `#${row.id}` }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="registration_type" label="申请类型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.registration_type === 'create' ? 'primary' : 'warning'" effect="light">
            {{ row.registration_type === 'create' ? '创建申请' : '修改申请' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="app_id_str" label="App ID" min-width="210" show-overflow-tooltip />
      <el-table-column prop="app_name" label="应用名称" min-width="150" show-overflow-tooltip />
      <el-table-column prop="owner_name" label="申请人" width="120" show-overflow-tooltip />
      <el-table-column prop="scopes" label="申请权限范围" min-width="260">
        <template #default="{ row }">
          <el-tag v-for="s in row.scopes" :key="s" size="small" class="hj-mr-4">
            {{ scopeNameOf(s) === s ? s : `${scopeNameOf(s)}（${s}）` }}
          </el-tag>
          <span v-if="!row.scopes?.length" class="hj-text-muted">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="审批状态" width="100">
        <template #default="{ row }">
          <el-tooltip v-if="row.approval_note" :content="row.approval_note" placement="top" :show-after="300">
            <el-tag :type="statusTagType(row.status)" effect="light">{{ statusLabel(row.status) }}</el-tag>
          </el-tooltip>
          <el-tag v-else :type="statusTagType(row.status)" effect="light">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="提交时间" width="170">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="handleDetail(row as AppRegistrationItem)">详情</el-button>
          <template v-if="row.status === 'pending'">
            <el-button size="small" type="primary" @click="handleApprovePass(row as AppRegistrationItem)"
              >通过</el-button
            >
            <el-button size="small" type="danger" @click="handleApproveReject(row as AppRegistrationItem)"
              >驳回</el-button
            >
          </template>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      class="hj-pagination hj-mt-20"
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      @current-change="fetchList"
      @size-change="handleSizeChange"
    />
  </el-card>

  <ApproveDialog v-model:visible="detailVisible" :record="detailRecord" readonly @submitted="onApproveSubmitted" />
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDateTime } from '@/utils/format'
import { listAppRegistrations, reviewAppRegistration } from '@/api/openapi'
import { fetchScopes, scopeNameOf } from '@/composables/useScopeCatalog'
import type { AppRegistrationItem } from '@/types/openapi'
import ApproveDialog from './components/ApproveDialog.vue'

const route = useRoute()

const list = ref<AppRegistrationItem[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const keyword = ref('')
const typeFilter = ref('')
const statusFilter = ref('')

const detailVisible = ref(false)
const detailRecord = ref<AppRegistrationItem | null>(null)

/** 审批状态 → 中文标签 */
function statusLabel(status: string): string {
  return { pending: '待审批', approved: '已通过', rejected: '已驳回' }[status] || status
}

/** 审批状态 → 标签配色 */
function statusTagType(status: string): 'info' | 'warning' | 'success' | 'danger' {
  return ({ pending: 'warning', approved: 'success', rejected: 'danger' }[status] || 'info') as
    'info' | 'warning' | 'success' | 'danger'
}

async function fetchList() {
  loading.value = true
  try {
    const res = await listAppRegistrations({
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value.trim() || undefined,
      registration_type: typeFilter.value || undefined,
      status: statusFilter.value || undefined,
    })
    list.value = res.data.items
    total.value = res.data.total
  } catch {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

function handleFilter() {
  page.value = 1
  fetchList()
}

function handleSizeChange() {
  page.value = 1
  fetchList()
}

/** 查看申请详情（只读：申请信息 + 审批结果，不含审批操作） */
function handleDetail(row: AppRegistrationItem) {
  detailRecord.value = row
  detailVisible.value = true
}

/** 审批通过：确认后直接提交（无需填写备注） */
async function handleApprovePass(row: AppRegistrationItem) {
  try {
    await ElMessageBox.confirm(
      `确认通过该「${row.registration_type === 'create' ? '创建' : '修改'}」申请？通过后应用将可正常调用开放接口。`,
      '通过申请',
      { type: 'info', confirmButtonText: '确认通过', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await reviewAppRegistration(row.id, { approved: true })
    ElMessage.success('已通过，应用可正常调用开放接口')
    fetchList()
  } catch {
    // 错误已处理
  }
}

/** 审批驳回：必须填写驳回原因，开发者将据此调整后重新提交 */
async function handleApproveReject(row: AppRegistrationItem) {
  try {
    const { value } = await ElMessageBox.prompt('请填写驳回原因（必填），开发者将据此调整后重新提交', '驳回申请', {
      inputType: 'textarea',
      inputPlaceholder: '请输入驳回原因',
      inputValidator: v => (v && v.trim().length > 0 ? true : '驳回原因不能为空'),
      confirmButtonText: '确认驳回',
      cancelButtonText: '取消',
      inputErrorMessage: '驳回原因不能为空',
    })
    await reviewAppRegistration(row.id, { approved: false, note: value.trim() })
    ElMessage.success('已驳回，开发者可调整后重新提交')
    fetchList()
  } catch {
    // 用户取消或请求失败
  }
}

/** 详情弹窗关闭后刷新（只读模式不会触发提交，保留兜底刷新） */
function onApproveSubmitted() {
  detailVisible.value = false
  fetchList()
}

onMounted(() => {
  const q = route.query.keyword
  if (q) keyword.value = String(q)
  void fetchScopes()
  fetchList()
})

// 全局搜索跳转携带 keyword 时自动过滤
watch(
  () => route.query.keyword,
  q => {
    if (q) {
      keyword.value = String(q)
      page.value = 1
      fetchList()
    }
  },
)
</script>

<style scoped>
.reg-id-text {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 12.5px;
  color: #409eff;
}
</style>
