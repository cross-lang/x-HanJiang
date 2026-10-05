<template>
  <div class="apps-page">
    <PageHead
      crumbs="应用管理"
      title="应用管理"
      desc="管理你的开放应用：创建应用并申请权限范围，审批通过后凭应用凭证调用开放接口。"
    />

    <div class="apps-card">
      <div class="apps-toolbar">
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

      <el-table :data="list" v-loading="loading" class="app-table">
        <el-table-column prop="app_id" label="App ID" width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <code class="app-id">{{ row.app_id }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="应用名称" width="150" />
        <el-table-column prop="auth_mode" label="鉴权模式" width="140">
          <template #default="{ row }">
            <span class="pill mode-pill" :class="`mode-${row.auth_mode}`">
              {{ row.auth_mode === 'plain' ? '明文' : row.auth_mode === 'hmac' ? 'HMAC 签名' : '双模式' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="scopes" label="权限范围" width="320">
          <template #default="{ row }">
            <span class="scope-chip">
              {{ scopeText(row.scopes[0]) }}
            </span>
            <el-popover
              v-if="row.scopes.length > 1"
              :width="280"
              trigger="click"
              placement="bottom-start"
            >
              <template #reference>
                <span class="scope-more scope-more-btn">+{{ row.scopes.length - 1 }}</span>
              </template>
              <div class="scope-pop-title">全部权限范围（{{ row.scopes.length }}）</div>
              <div class="scope-pop-list">
                <span v-for="s in row.scopes" :key="s" class="scope-pop-item">
                  {{ scopeText(s) }}
                </span>
              </div>
            </el-popover>
            <span v-if="row.scopes.length === 0" class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="approval_status" label="审批状态" width="130" header-align="center">
          <template #default="{ row }">
            <span
              class="pill"
              :class="
                row.approval_status === 'approved'
                  ? 'st-approved'
                  : row.approval_status === 'pending'
                    ? 'st-pending'
                    : row.approval_status === 'rejected'
                      ? 'st-rejected'
                      : 'st-none'
              "
            >
              {{ row.approval_status === 'approved' ? '已通过' : row.approval_status === 'pending' ? '待审批' : row.approval_status === 'rejected' ? '已驳回' : '未申请' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" header-align="center">
          <template #default="{ row }">
            <span class="pill" :class="row.status === 'active' ? 'st-approved' : 'st-disabled'">
              {{ row.status === 'active' ? '启用' : '禁用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="updated_at" label="最后修改时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="330" fixed="right">
          <template #default="{ row }">
            <!-- 被管理员禁用的应用：不能执行任何操作，仅可删除与查看申请记录 -->
            <template v-if="row.status === 'disabled'">
              <el-button size="small" type="danger" plain @click="handleDelete(row as OpenAppItem)">删除</el-button>
              <el-button size="small" text @click="handleApprovals(row as OpenAppItem)">申请记录</el-button>
            </template>
            <template v-else>
              <el-button
                size="small"
                type="primary"
                :disabled="row.approval_status === 'pending'"
                @click="handleApplyScope(row as OpenAppItem)"
              >
                申请权限
              </el-button>
              <el-button
                size="small"
                :disabled="row.approval_status === 'pending'"
                @click="handleEdit(row as OpenAppItem)"
              >
                编辑
              </el-button>
              <el-button size="small" @click="handleApprovals(row as OpenAppItem)">申请记录</el-button>
              <el-dropdown trigger="click" @command="(cmd: string) => handleMore(cmd, row as OpenAppItem)">
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
    </div>

    <AppFormDialog v-model:visible="dialogVisible" mode="create" @created="onAppCreated" />
    <AppFormDialog v-model:visible="editDialogVisible" mode="edit" :record="editRecord" @submitted="onDialogSubmitted" />
    <ScopeApplyDialog v-model:visible="scopeDialogVisible" :record="scopeRecord" @submitted="onScopeSubmitted" />
    <ApprovalRecordsDialog v-model:visible="approvalDialogVisible" :record="approvalRecord" />

    <SecretResultDialog
      v-model:visible="rotateResultVisible"
      title="App Key 重置成功"
      type="warning"
      :secret="rotateResult"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Key, MoreFilled } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/format'
import { listMyApps, deleteApp, rotateAppKey } from '@/api/apps'
import { fetchScopes, scopeNameOf } from '@/composables/useScopeCatalog'
import type { OpenAppItem } from '@/types/app'
import PageHead from '@/components/PageHead.vue'
import AppFormDialog, { type AppSecret } from './components/AppFormDialog.vue'
import ScopeApplyDialog from './components/ScopeApplyDialog.vue'
import ApprovalRecordsDialog from './components/ApprovalRecordsDialog.vue'
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

const approvalDialogVisible = ref(false)
const approvalRecord = ref<OpenAppItem | null>(null)

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

/** 权限范围单元格文案：中文名 + 编码（无中文名时回退为编码本身） */
function scopeText(s: string | undefined): string {
  if (!s) return ''
  const name = scopeNameOf(s)
  return name === s ? s : `${name}（${s}）`
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

/** 更多（···）下拉：重置密钥 / 删除（编辑 / 申请权限 / 申请记录 已在操作列直接展示） */
function handleMore(cmd: string, row: OpenAppItem) {
  if (cmd === 'rotate') {
    handleRotateKey(row)
  } else if (cmd === 'delete') {
    handleDelete(row)
  }
}

/** 查看应用全部申请记录（弹窗） */
function handleApprovals(row: OpenAppItem) {
  approvalRecord.value = row
  approvalDialogVisible.value = true
}

/** 创建成功：提示申请已提交并刷新列表（创建后无明文密钥，密钥待审批通过后可用） */
function onAppCreated() {
  ElMessage.success('创建申请已提交，等待管理员审批')
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
  // 承接全局搜索跳转携带的 keyword（/apps?keyword=xxx），回填输入框并过滤列表
  const q = useRoute().query.keyword
  if (typeof q === 'string' && q.trim()) {
    keyword.value = q.trim()
  }
  fetchList()
})
</script>

<style scoped>
.apps-page {
  /* 表格型页面保持全宽，不限制 max-width（文档型页面才居中限宽） */
  padding: 4px 4px 24px;
}

/* ─── 列表卡片（对齐 doc-section 风格） ─── */
.apps-card {
  background: var(--hj-bg-card);
  border: 1px solid var(--hj-border-light);
  border-radius: var(--hj-radius-lg);
  padding: 18px 22px 8px;
  margin-bottom: 18px;
  box-shadow: var(--hj-shadow-card);
}
.apps-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

/* ─── 表格（对齐开放能力页 doc-table 风格） ─── */
.app-table {
  width: 100%;
  --el-table-border-color: var(--hj-border-light);
  --el-table-header-bg-color: var(--hj-bg-page);
  --el-table-row-hover-bg-color: var(--hj-bg-hover);
}
.app-table :deep(th.el-table__cell) {
  background: #f7f8fa;
  color: var(--hj-text-title);
  font-weight: 600;
  font-size: 13px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--hj-border-light);
  white-space: nowrap;
}
.app-table :deep(td.el-table__cell) {
  padding: 12px 16px;
  font-size: 13px;
  color: var(--hj-text-regular);
  border-bottom: 1px solid var(--hj-border-lighter);
}
.app-table :deep(.cell) {
  line-height: 1.7;
}
.app-id {
  font-family: var(--hj-font-mono);
  font-size: 12.5px;
  color: var(--hj-text-title);
  word-break: break-all;
}

/* ─── 徽章（胶囊小标签） ─── */
.pill {
  display: inline-block;
  font-size: 12px;
  line-height: 22px;
  padding: 0 10px;
  border-radius: 999px;
  white-space: nowrap;
}
.mode-plain {
  color: #e6a23c;
  background: #fdf6ec;
  border: 1px solid #f5dab1;
}
.mode-hmac {
  color: #67c23a;
  background: #f0f9eb;
  border: 1px solid #c2e7b0;
}
.mode-both {
  color: var(--hj-primary);
  background: var(--hj-primary-bg);
  border: 1px solid var(--hj-primary-border);
}
.st-approved {
  color: #67c23a;
  background: #f0f9eb;
  border: 1px solid #c2e7b0;
}
.st-pending {
  color: #e6a23c;
  background: #fdf6ec;
  border: 1px solid #f5dab1;
}
.st-rejected {
  color: #f56c6c;
  background: #fef0f0;
  border: 1px solid #fbc4c4;
}
.st-none {
  color: var(--hj-text-secondary);
  background: #f4f4f5;
  border: 1px solid #e8e8ea;
}
.st-disabled {
  color: #909399;
  background: #f4f4f5;
  border: 1px solid #e8e8ea;
}
.scope-chip {
  display: inline-block;
  margin: 2px 4px 2px 0;
  font-size: 12px;
  line-height: 22px;
  padding: 0 8px;
  border-radius: 6px;
  color: var(--hj-primary);
  background: var(--hj-primary-bg);
  white-space: nowrap;
}
.scope-more {
  display: inline-block;
  font-size: 12px;
  line-height: 22px;
  padding: 0 6px;
  border-radius: 6px;
  color: var(--hj-text-secondary);
  background: #f4f4f5;
  white-space: nowrap;
}
.scope-more-btn {
  cursor: pointer;
  transition: all 0.15s ease;
}
.scope-more-btn:hover {
  color: var(--hj-primary);
  background: var(--hj-primary-bg);
}
.scope-pop-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--hj-text-title);
  margin-bottom: 10px;
}
.scope-pop-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.scope-pop-item {
  display: inline-block;
  font-size: 12.5px;
  line-height: 22px;
  padding: 0 8px;
  border-radius: 6px;
  color: var(--hj-primary);
  background: var(--hj-primary-bg);
  white-space: nowrap;
  align-self: flex-start;
}
.text-muted {
  color: var(--hj-text-muted);
}

/* ─── 操作列 ─── */
.more-btn {
  margin-left: 4px;
  padding: 6px;
  border-radius: 6px;
  transition: background 0.15s ease, color 0.15s ease;
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
</style>
