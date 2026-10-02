<template>
  <el-card>
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
          <el-tag v-for="s in row.scopes" :key="s" size="small" class="hj-mr-4">{{ s }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'danger'">{{
            row.status === 'active' ? '启用' : '禁用'
          }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="owner_name" label="拥有者" width="120" />
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
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
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDateTime } from '@/utils/format'
import { listApps, updateAppStatus, rotateAppKey, deleteApp } from '@/api/openapi'
import type { OpenAppItem } from '@/types/openapi'
import AppFormDialog, { type AppSecret } from './components/AppFormDialog.vue'
import SecretResultDialog from './components/SecretResultDialog.vue'

const route = useRoute()

const list = ref<OpenAppItem[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const keyword = ref('')

const dialogVisible = ref(false)
const editDialogVisible = ref(false)
const editRecord = ref<OpenAppItem | null>(null)

const resultVisible = ref(false)
const createdApp = ref<AppSecret>({ app_id: '', app_key: '' })

const rotateResultVisible = ref(false)
const rotateResult = ref<AppSecret>({ app_id: '', app_key: '' })

async function fetchList() {
  loading.value = true
  try {
    const res = await listApps({
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value.trim() || undefined,
    })
    list.value = res.data.items
    total.value = res.data.total
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
