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
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="handleDetail(row as AppRegistrationItem)">详情</el-button>
          <el-button
            v-if="row.status === 'pending'"
            size="small"
            type="primary"
            @click="handleApprove(row as AppRegistrationItem)"
          >
            审批
          </el-button>
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

  <ApproveDialog v-model:visible="approveVisible" :record="approveRecord" @submitted="onApproveSubmitted" />
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { formatDateTime } from '@/utils/format'
import { listAppRegistrations } from '@/api/openapi'
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

const approveVisible = ref(false)
const approveRecord = ref<AppRegistrationItem | null>(null)

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

/** 查看申请详情（含快照与审批意见） */
function handleDetail(row: AppRegistrationItem) {
  // 复用审批弹窗展示批次详情；无审批按钮的终态批次仅查看
  approveRecord.value = row
  approveVisible.value = true
}

function handleApprove(row: AppRegistrationItem) {
  approveRecord.value = row
  approveVisible.value = true
}

/** 审批提交成功：关闭并刷新列表 */
function onApproveSubmitted() {
  approveVisible.value = false
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
