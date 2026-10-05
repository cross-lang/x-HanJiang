<template>
  <el-card>
    <el-tabs v-model="scopeTab" class="hj-app-scope-tabs" @tab-change="handleScopeChange">
      <el-tab-pane label="全部应用" name="all" />
      <el-tab-pane label="我新建的" name="created" />
      <el-tab-pane label="我审批的" name="approved" />
    </el-tabs>
    <div class="hj-toolbar">
      <el-button type="primary" @click="handleCreate">新建应用</el-button>
      <div class="hj-flex hj-gap-8">
        <el-input
          v-model="keyword"
          placeholder="按应用名称/App ID搜索"
          style="width: 230px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-button type="primary" icon="Search" @click="handleSearch">搜索</el-button>
      </div>
    </div>
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="app_id" label="App ID" width="200" />
      <el-table-column prop="name" label="应用名称" />
      <el-table-column prop="auth_mode" label="鉴权模式" width="110">
        <template #default="{ row }">
          <el-tag v-if="row.auth_mode === 'plain'" type="warning">明文</el-tag>
          <el-tag v-else-if="row.auth_mode === 'hmac'" type="success">HMAC 签名</el-tag>
          <el-tag v-else type="primary">双模式</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="scopes" label="权限范围">
        <template #default="{ row }">
          <el-tag v-for="s in row.scopes" :key="s" size="small" class="hj-mr-4">
            {{ scopeNameOf(s) === s ? s : `${scopeNameOf(s)}（${s}）` }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'danger'">{{
            row.status === 'active' ? '启用' : '禁用'
          }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="审批状态" width="110">
        <template #default="{ row }">
          <span v-if="!row.approval_status" class="hj-approval-none">-</span>
          <el-tooltip v-else-if="row.approval_note" :content="row.approval_note" placement="top" :show-after="300">
            <el-tag :type="approvalTagType(row.approval_status)" effect="light">
              {{ approvalLabel(row.approval_status) }}
            </el-tag>
          </el-tooltip>
          <el-tag v-else :type="approvalTagType(row.approval_status)" effect="light">
            {{ approvalLabel(row.approval_status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="owner_name" label="拥有者" width="120" />
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="340" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.approval_status === 'pending'"
            size="small"
            type="primary"
            @click="handleApprove(row as OpenAppItem)"
          >
            审批
          </el-button>
          <el-button size="small" @click="handleEdit(row as OpenAppItem)">编辑</el-button>
          <el-button size="small" type="warning" @click="handleRotateKey(row as OpenAppItem)">重置密钥</el-button>
          <el-button
            size="small"
            :type="row.status === 'active' ? 'warning' : 'success'"
            @click="handleToggleStatus(row as OpenAppItem)"
          >
            {{ row.status === 'active' ? '禁用' : '启用' }}
          </el-button>
          <el-button size="small" type="danger" @click="handleDelete(row as OpenAppItem)">删除</el-button>
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

  <AppFormDialog v-model:visible="dialogVisible" mode="create" @created="onAppCreated" />
  <AppFormDialog v-model:visible="editDialogVisible" mode="edit" :record="editRecord" @submitted="onDialogSubmitted" />

  <SecretResultDialog v-model:visible="resultVisible" title="应用创建成功" type="success" :secret="createdApp" />

  <SecretResultDialog
    v-model:visible="rotateResultVisible"
    title="App Key 重置成功"
    type="warning"
    :secret="rotateResult"
  />

  <ApproveDialog v-model:visible="approveVisible" :record="approveRecord" @submitted="onApproveSubmitted" />
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDateTime } from '@/utils/format'
import { listApps, updateAppStatus, rotateAppKey, deleteApp } from '@/api/openapi'
import { fetchScopes, scopeNameOf } from '@/composables/useScopeCatalog'
import type { OpenAppItem } from '@/types/openapi'
import AppFormDialog, { type AppSecret } from './components/AppFormDialog.vue'
import ApproveDialog from './components/ApproveDialog.vue'
import SecretResultDialog from './components/SecretResultDialog.vue'

const route = useRoute()

const list = ref<OpenAppItem[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const keyword = ref('')
const scopeTab = ref('all')

const dialogVisible = ref(false)
const editDialogVisible = ref(false)
const editRecord = ref<OpenAppItem | null>(null)

const resultVisible = ref(false)
const createdApp = ref<AppSecret>({ app_id: '', app_key: '' })

const rotateResultVisible = ref(false)
const rotateResult = ref<AppSecret>({ app_id: '', app_key: '' })

const approveVisible = ref(false)
const approveRecord = ref<OpenAppItem | null>(null)

/** 审批状态徽章类型 */
function approvalTagType(status: string | null) {
  if (!status) return 'info'
  if (status === 'approved') return 'success'
  if (status === 'rejected') return 'danger'
  return 'warning'
}

/** 审批状态中文标签 */
function approvalLabel(status: string | null) {
  if (!status) return '-'
  if (status === 'approved') return '已通过'
  if (status === 'rejected') return '已驳回'
  return '待审批'
}

async function fetchList() {
  loading.value = true
  try {
    const res = await listApps({
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value.trim() || undefined,
      scope: scopeTab.value === 'all' ? undefined : (scopeTab.value as 'created' | 'approved'),
    })
    list.value = res.data.items
    total.value = res.data.total
  } catch {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

function handleScopeChange() {
  page.value = 1
  fetchList()
}

function handleSearch() {
  page.value = 1
  fetchList()
}

function handleSizeChange() {
  page.value = 1
  fetchList()
}

function handleCreate() {
  dialogVisible.value = true
}

function handleEdit(row: OpenAppItem) {
  editRecord.value = row
  editDialogVisible.value = true
}

/** 创建成功：展示密钥弹窗并刷新列表 */
function onAppCreated(secret: AppSecret) {
  createdApp.value = secret
  resultVisible.value = true
  fetchList()
}

/** 编辑成功：关闭并刷新列表 */
function onDialogSubmitted() {
  editDialogVisible.value = false
  fetchList()
}

/** 打开审批对话框（仅待审批应用显示入口） */
function handleApprove(row: OpenAppItem) {
  approveRecord.value = row
  approveVisible.value = true
}

/** 审批提交成功：关闭并刷新列表 */
function onApproveSubmitted() {
  approveVisible.value = false
  fetchList()
}

async function handleToggleStatus(row: OpenAppItem) {
  const newStatus = row.status === 'active' ? 'disabled' : 'active'
  try {
    await ElMessageBox.confirm(
      `确定${newStatus === 'active' ? '启用' : '禁用'}应用「${row.name}」吗？`,
      '危险操作确认',
      { type: 'warning' },
    )
  } catch {
    return
  }
  try {
    await updateAppStatus(row.id, newStatus)
    ElMessage.success(newStatus === 'active' ? '已启用' : '已禁用')
    fetchList()
  } catch {
    // 错误已处理
  }
}

async function handleRotateKey(row: OpenAppItem) {
  try {
    await ElMessageBox.confirm(
      `确定重置应用「${row.name}」的 App Key 吗？重置后旧 Key 将立即失效，所有正在使用旧 Key 的调用都会失败！`,
      '危险操作确认',
      { type: 'warning', confirmButtonText: '确定重置' },
    )
  } catch {
    return
  }
  try {
    const res = await rotateAppKey(row.id)
    rotateResult.value = { app_id: res.data.app_id, app_key: res.data.app_key }
    rotateResultVisible.value = true
  } catch {
    // 错误已处理
  }
}

async function handleDelete(row: OpenAppItem) {
  try {
    await ElMessageBox.confirm(
      `确定删除应用「${row.name}」吗？删除后该应用将无法调用任何接口，此操作不可撤销！`,
      '危险操作确认',
      { type: 'error', confirmButtonText: '确定删除' },
    )
  } catch {
    return
  }
  try {
    await deleteApp(row.id)
    ElMessage.success('删除成功')
    fetchList()
  } catch {
    // 错误已处理
  }
}

onMounted(() => {
  const q = route.query.keyword
  if (q) keyword.value = String(q)
  // scope 目录用于权限范围列中文名展示（失败时回退为裸编码）
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
