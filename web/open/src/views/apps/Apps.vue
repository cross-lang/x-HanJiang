<template>
  <el-card>
    <div class="hj-flex-between hj-mb-16">
      <el-button type="primary" icon="Plus" @click="handleCreate">新建应用</el-button>
      <div class="hj-flex hj-gap-8">
        <el-input
          v-model="keyword"
          placeholder="按应用名称 / App ID 搜索"
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
      <el-table-column prop="app_id" label="App ID" width="190" />
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
      <el-table-column prop="approval_status" label="审批状态" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.approval_status === 'approved'" type="success">已通过</el-tag>
          <el-tag v-else-if="row.approval_status === 'pending'" type="warning">待审批</el-tag>
          <el-tag v-else-if="row.approval_status === 'rejected'" type="danger">已驳回</el-tag>
          <el-tag v-else type="info">未申请</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'danger'">{{
            row.status === 'active' ? '启用' : '禁用'
          }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="210" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="handleApplyScope(row as OpenAppItem)">申请权限</el-button>
          <el-button size="small" type="warning" @click="handleRotateKey(row as OpenAppItem)">重置密钥</el-button>
          <el-dropdown trigger="click" @command="(cmd: string) => handleMore(cmd, row as OpenAppItem)">
            <el-button size="small" text class="more-btn">
              <el-icon><MoreFilled /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="edit">
                  <el-icon class="menu-icon"><Edit /></el-icon>编辑
                </el-dropdown-item>
                <el-dropdown-item command="delete" divided class="danger-item">
                  <el-icon class="menu-icon"><Delete /></el-icon>删除
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      class="hj-pagination"
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      @current-change="fetchList"
      @size-change="handleSizeChange"
    />
  </el-card>

  <AppFormDialog v-model:visible="dialogVisible" mode="create" @created="onAppCreated" />
  <AppFormDialog v-model:visible="editDialogVisible" mode="edit" :record="editRecord" @submitted="onDialogSubmitted" />
  <ScopeApplyDialog v-model:visible="scopeDialogVisible" :record="scopeRecord" @submitted="onScopeSubmitted" />

  <SecretResultDialog v-model:visible="resultVisible" title="应用创建成功" type="success" :secret="createdApp" />
  <SecretResultDialog
    v-model:visible="rotateResultVisible"
    title="App Key 重置成功"
    type="warning"
    :secret="rotateResult"
  />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, MoreFilled } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/format'
import { listMyApps, deleteApp, rotateAppKey } from '@/api/apps'
import { fetchScopes, scopeNameOf } from '@/composables/useScopeCatalog'
import type { OpenAppItem } from '@/types/app'
import AppFormDialog, { type AppSecret } from './components/AppFormDialog.vue'
import ScopeApplyDialog from './components/ScopeApplyDialog.vue'
import SecretResultDialog from '@/components/SecretResultDialog.vue'

const list = ref<OpenAppItem[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const keyword = ref('')

const dialogVisible = ref(false)
const editDialogVisible = ref(false)
const editRecord = ref<OpenAppItem | null>(null)

const scopeDialogVisible = ref(false)
const scopeRecord = ref<OpenAppItem | null>(null)

const resultVisible = ref(false)
const createdApp = ref<AppSecret>({ app_id: '', app_key: '' })

const rotateResultVisible = ref(false)
const rotateResult = ref<AppSecret>({ app_id: '', app_key: '' })

async function fetchList() {
  loading.value = true
  try {
    const res = await listMyApps({
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

function handleApplyScope(row: OpenAppItem) {
  scopeRecord.value = row
  scopeDialogVisible.value = true
}

/** 更多（···）下拉：编辑 / 删除 */
function handleMore(cmd: string, row: OpenAppItem) {
  if (cmd === 'edit') {
    handleEdit(row)
  } else if (cmd === 'delete') {
    handleDelete(row)
  }
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

/** scope 申请提交成功：关闭并刷新列表 */
function onScopeSubmitted() {
  scopeDialogVisible.value = false
  fetchList()
}

async function handleRotateKey(row: OpenAppItem) {
  try {
    await ElMessageBox.confirm(
      `确定重置应用「${row.name}」的 App Key 吗？重置后旧 Key 将立即失效！`,
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
  // scope 目录用于权限范围列中文名展示（失败时回退为裸编码）
  void fetchScopes()
  fetchList()
})
</script>

<style scoped>
.more-btn {
  margin-left: 4px;
  padding: 6px;
}
.menu-icon {
  margin-right: 6px;
}
.danger-item {
  color: #f56c6c;
}
</style>
