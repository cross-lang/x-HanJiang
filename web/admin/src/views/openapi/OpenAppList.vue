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
      <el-table-column prop="app_id" label="App ID" min-width="210" show-overflow-tooltip />
      <el-table-column prop="name" label="应用名称" min-width="150" />
      <el-table-column prop="auth_mode" label="鉴权模式" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.auth_mode === 'plain'" type="warning">明文</el-tag>
          <el-tag v-else-if="row.auth_mode === 'hmac'" type="success">HMAC 签名</el-tag>
          <el-tag v-else type="primary">双模式</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="scopes" label="权限范围" min-width="220">
        <template #default="{ row }">
          <template v-if="row.scopes && row.scopes.length > 0">
            <el-tag size="small" class="hj-mr-4">{{ scopeLabel(row.scopes[0]) }}</el-tag>
            <el-button
              v-if="row.scopes.length > 1"
              size="small"
              text
              type="primary"
              @click="openScopes(row as OpenAppItem)"
            >
              +{{ row.scopes.length - 1 }}
            </el-button>
          </template>
          <span v-else class="hj-text-muted">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'danger'">{{
            row.status === 'active' ? '启用' : '禁用'
          }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="owner_name" label="归属人" width="120" />
      <el-table-column prop="owner_type" label="归属类型" width="110">
        <template #default="{ row }">
          <el-tag :type="row.owner_type === 'developer' ? 'primary' : 'info'" effect="light">
            {{ row.owner_type === 'developer' ? '开发者自助' : '管理员分配' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="handleEdit(row as OpenAppItem)">编辑</el-button>
          <el-button
            size="small"
            :type="row.status === 'active' ? 'warning' : 'success'"
            @click="handleToggleStatus(row as OpenAppItem)"
          >
            {{ row.status === 'active' ? '禁用' : '启用' }}
          </el-button>
          <!-- 开发者自助应用的密钥/删除权限归开发者本人（门户端），管理端不代操作；
               无更多操作时不展示"更多"按钮 -->
          <el-dropdown
            v-if="row.owner_type !== 'developer'"
            trigger="click"
            @command="(cmd: string) => handleMore(cmd, row as OpenAppItem)"
          >
            <el-button size="small" text class="more-btn">
              <el-icon><MoreFilled /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="rotate">
                  <el-icon class="menu-icon"><Key /></el-icon>重置密钥
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

  <!-- 权限范围全部权限查看弹窗 -->
  <el-dialog v-model="scopesVisible" :title="scopesTitle" width="480px" top="18vh">
    <div class="scope-dialog-body">
      <el-tag v-for="s in scopesAll" :key="s" size="small" class="scope-dialog-tag">
        {{ scopeLabel(s) }}
      </el-tag>
      <span v-if="scopesAll.length === 0" class="hj-text-muted">暂无权限范围</span>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Key, MoreFilled } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/format'
import { listApps, updateAppStatus, rotateAppKey, deleteApp } from '@/api/openapi'
import { fetchScopes, scopeNameOf } from '@/composables/useScopeCatalog'
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

const scopesVisible = ref(false)
const scopesTitle = ref('')
const scopesAll = ref<string[]>([])

/** 单权限项展示文案：有中文名则「中文（编码）」，否则原样编码 */
function scopeLabel(s: string): string {
  const name = scopeNameOf(s)
  return name === s ? s : `${name}（${s}）`
}

/** 点击 +N 查看该应用全部权限范围 */
function openScopes(row: OpenAppItem) {
  scopesAll.value = row.scopes || []
  scopesTitle.value = `权限范围 — ${row.name}`
  scopesVisible.value = true
}

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

/** 更多（···）下拉：重置密钥 / 删除 */
function handleMore(cmd: string, row: OpenAppItem) {
  if (cmd === 'rotate') {
    handleRotateKey(row)
  } else if (cmd === 'delete') {
    handleDelete(row)
  }
}

async function handleToggleStatus(row: OpenAppItem) {
  const newStatus = row.status === 'active' ? 'disabled' : 'active'
  try {
    await ElMessageBox.confirm(
      `确定${newStatus === 'active' ? '启用' : '禁用'}应用「${row.name}」吗？${
        newStatus === 'disabled'
          ? '\n禁用后该应用的全部 API 调用立即被拒绝；若该应用存在待审批的权限申请，将一并拒绝。'
          : ''
      }`,
      '危险操作确认',
      { type: 'warning', confirmButtonText: newStatus === 'active' ? '确认启用' : '确认禁用' },
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

<style scoped>
.more-btn {
  margin-left: 4px;
  padding: 6px;
  border-radius: 6px;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}
.more-btn:hover {
  background: var(--hj-bg-hover);
  color: var(--hj-primary);
}
.menu-icon {
  margin-right: 6px;
}
.danger-item {
  color: #f56c6c;
}
.scope-dialog-body {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.scope-dialog-tag {
  line-height: 22px;
}
</style>
