<template>
  <el-card>
    <div class="hj-toolbar">
      <div class="hj-flex hj-gap-8">
        <el-select v-model="statusFilter" placeholder="账号状态" style="width: 130px" clearable @change="handleSearch">
          <el-option label="启用" value="enabled" />
          <el-option label="禁用" value="disabled" />
        </el-select>
        <el-input
          v-model="keyword"
          placeholder="按用户名/邮箱/姓名搜索"
          style="width: 230px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-button type="primary" icon="Search" @click="handleSearch">搜索</el-button>
      </div>
    </div>
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="name" label="姓名" />
      <el-table-column prop="email" label="邮箱" />
      <el-table-column prop="phone" label="手机号" width="130" />
      <el-table-column label="认证状态" width="100">
        <template #default="{ row }">
          <el-tag :type="certTagType((row as DeveloperItem).certification_status)" effect="light">
            {{ certLabel((row as DeveloperItem).certification_status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="账号状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'enabled' ? 'success' : 'danger'">
            {{ row.status === 'enabled' ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="app_count" label="旗下应用" width="90" align="center" />
      <el-table-column prop="last_login_at" label="最后登录" width="170">
        <template #default="{ row }">
          {{ row.last_login_at ? formatDateTime(row.last_login_at) : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="110" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" plain @click="handleViewApps(row as DeveloperItem)"
            >查看应用</el-button
          >
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

  <!-- 开发者旗下应用列表弹窗 -->
  <el-dialog v-model="appsVisible" :title="`应用列表 — ${appsOwnerName}`" width="860px" top="8vh">
    <div class="hj-toolbar">
      <div class="hj-flex hj-gap-8">
        <el-input
          v-model="appsKeyword"
          placeholder="按应用名称搜索"
          style="width: 230px"
          clearable
          @keyup.enter="fetchApps"
          @clear="fetchApps"
        />
        <el-button type="primary" icon="Search" @click="fetchApps">搜索</el-button>
      </div>
    </div>
    <el-table :data="appsList" v-loading="appsLoading" height="420">
      <el-table-column prop="app_id" label="App ID" min-width="210" show-overflow-tooltip />
      <el-table-column prop="name" label="应用名称" min-width="150" />
      <el-table-column prop="auth_mode" label="鉴权模式" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.auth_mode === 'plain'" type="warning">明文</el-tag>
          <el-tag v-else-if="row.auth_mode === 'hmac'" type="success">HMAC 签名</el-tag>
          <el-tag v-else type="primary">双模式</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="scopes" label="权限范围" min-width="240">
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
      <el-table-column label="审批状态" width="100">
        <template #default="{ row }">
          <span v-if="!row.approval_status" class="hj-approval-none">-</span>
          <el-tag v-else :type="approvalTagType(row.approval_status)" effect="light">
            {{ approvalLabel(row.approval_status) }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      class="hj-pagination hj-mt-20"
      v-model:current-page="appsPage"
      v-model:page-size="appsPageSize"
      :total="appsTotal"
      @current-change="fetchApps"
      @size-change="fetchApps"
    />
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { formatDateTime } from '@/utils/format'
import { listDevelopers, listDeveloperApps } from '@/api/openapi'
import { fetchScopes, scopeNameOf } from '@/composables/useScopeCatalog'
import type { DeveloperItem, OpenAppItem } from '@/types/openapi'

const list = ref<DeveloperItem[]>([])
const loading = ref(false)
const keyword = ref('')
const statusFilter = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 旗下应用弹窗
const appsVisible = ref(false)
const appsLoading = ref(false)
const appsList = ref<OpenAppItem[]>([])
const appsKeyword = ref('')
const appsPage = ref(1)
const appsPageSize = ref(10)
const appsTotal = ref(0)
const appsOwnerName = ref('')
let appsOwnerId = 0

/** 认证状态 → 中文标签 */
function certLabel(status: string): string {
  return (
    {
      none: '未认证',
      pending: '审批中',
      approved: '已认证',
      rejected: '已驳回',
    }[status] || status
  )
}

/** 认证状态 → 标签配色 */
function certTagType(status: string): 'info' | 'warning' | 'success' | 'danger' {
  return ({
    none: 'info',
    pending: 'warning',
    approved: 'success',
    rejected: 'danger',
  }[status] || 'info') as 'info' | 'warning' | 'success' | 'danger'
}

/** 审批状态 → 中文标签 */
function approvalLabel(status: string): string {
  return (
    {
      pending: '待审批',
      approved: '已通过',
      rejected: '已驳回',
    }[status] || status
  )
}

/** 审批状态 → 标签配色 */
function approvalTagType(status: string): 'warning' | 'success' | 'danger' {
  return ({
    pending: 'warning',
    approved: 'success',
    rejected: 'danger',
  }[status] || 'info') as 'warning' | 'success' | 'danger'
}

async function fetchList() {
  loading.value = true
  try {
    const res = await listDevelopers({
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value || undefined,
      status: statusFilter.value || undefined,
    })
    list.value = res.data.items
    total.value = res.data.total
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

async function handleViewApps(row: DeveloperItem) {
  appsOwnerId = row.id
  appsOwnerName.value = `${row.name || row.username}（${row.username}）`
  appsKeyword.value = ''
  appsPage.value = 1
  appsVisible.value = true
  await fetchApps()
}

async function fetchApps() {
  if (!appsOwnerId) return
  appsLoading.value = true
  try {
    const res = await listDeveloperApps(appsOwnerId, {
      page: appsPage.value,
      page_size: appsPageSize.value,
      keyword: appsKeyword.value || undefined,
    })
    appsList.value = res.data.items
    appsTotal.value = res.data.total
  } finally {
    appsLoading.value = false
  }
}

// 页面打开时预取 scope 目录（应用权限范围标签用）
fetchScopes()
fetchList()
</script>
