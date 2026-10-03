<template>
  <el-card>
    <div class="hj-toolbar">
      <el-button type="primary" @click="handleCreate">新建用户</el-button>
      <div class="hj-flex hj-gap-8">
        <el-input
          v-model="keyword"
          placeholder="按用户名/姓名/邮箱搜索"
          style="width: 230px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-button type="primary" icon="Search" @click="handleSearch">搜索</el-button>
        <el-button icon="Download" @click="handleExport">导出CSV</el-button>
      </div>
    </div>
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="name" label="姓名" />
      <el-table-column label="性别" width="70">
        <template #default="{ row }">{{
          row.gender === 'male' ? '男' : row.gender === 'female' ? '女' : '-'
        }}</template>
      </el-table-column>
      <el-table-column prop="email" label="邮箱" />
      <el-table-column prop="phone" label="手机号" width="130" />
      <el-table-column label="角色" width="150">
        <template #default="{ row }">
          {{ (row as UserItem).roles?.length ? (row as UserItem).roles.map(r => r.role_name).join('；') : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'enabled' ? 'success' : 'danger'">
            {{ row.status === 'enabled' ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <template v-if="canOperate(row as UserItem)">
            <el-button
              v-if="row.status !== 'enabled' && row.username !== 'superadmin'"
              size="small"
              type="success"
              @click="handleToggleStatus(row as UserItem, 'enabled')"
              >启用</el-button
            >
            <el-button
              v-if="row.status === 'enabled' && row.username !== 'superadmin'"
              size="small"
              type="warning"
              @click="handleToggleStatus(row as UserItem, 'disabled')"
              >禁用</el-button
            >
            <el-button v-if="row.username !== 'superadmin'" size="small" @click="handleEdit(row as UserItem)"
              >编辑</el-button
            >
            <el-button
              v-if="row.id !== userStore.userInfo?.id"
              size="small"
              @click="handleResetPassword(row as UserItem)"
              >重置密码</el-button
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

  <UserFormDialog
    v-model:visible="dialogVisible"
    :mode="isEdit ? 'edit' : 'create'"
    :record="editRecord"
    @submitted="onUserSubmitted"
  />

  <el-dialog v-model="resetVisible" title="重置密码">
    <p style="margin-bottom: 15px">
      重置用户 <strong>{{ resetUser?.username }}</strong> 的密码
    </p>
    <el-input v-model="resetPassword" type="password" placeholder="请输入新密码" show-password />
    <template #footer>
      <el-button @click="resetVisible = false">取消</el-button>
      <el-button type="primary" @click="confirmResetPassword">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { formatDateTime } from '@/utils/format'
import { downloadResponseBlob } from '@/utils/download'
import { listUsers, updateUser, resetUserPassword, exportUsersCsv } from '@/api/user'
import type { UserItem } from '@/types/user'
import UserFormDialog from './components/UserFormDialog.vue'

const route = useRoute()
const userStore = useUserStore()
const list = ref<UserItem[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const keyword = ref('')

const dialogVisible = ref(false)
const isEdit = ref(false)
const editRecord = ref<UserItem | null>(null)

const resetVisible = ref(false)
const resetUser = ref<UserItem | null>(null)
const resetPassword = ref('')

async function fetchList() {
  loading.value = true
  try {
    const res = await listUsers({
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
  isEdit.value = false
  editRecord.value = null
  dialogVisible.value = true
}

function handleEdit(row: UserItem) {
  isEdit.value = true
  editRecord.value = row
  dialogVisible.value = true
}

/** 表单弹窗提交成功：关闭并刷新列表 */
function onUserSubmitted() {
  dialogVisible.value = false
  fetchList()
}

async function handleToggleStatus(row: UserItem, status: string) {
  const action = status === 'enabled' ? '启用' : '禁用'
  try {
    await ElMessageBox.confirm(`确定要${action}用户 ${row.username} 吗？`, '提示', { type: 'warning' })
    await updateUser(row.id, { status })
    ElMessage.success(`${action}成功`)
    fetchList()
  } catch {
    // 取消或错误
  }
}

function handleResetPassword(row: UserItem) {
  resetUser.value = row
  resetVisible.value = true
}

async function confirmResetPassword() {
  if (!resetUser.value) return
  try {
    await resetUserPassword(resetUser.value.id, resetPassword.value)
    ElMessage.success('密码已重置')
    resetVisible.value = false
  } catch {
    // 错误已处理
  }
}

function canOperate(row: UserItem): boolean {
  // 超级管理员才能操作超级管理员
  if (row.username === 'superadmin') {
    return userStore.userInfo?.username === 'superadmin'
  }
  return true
}

async function handleExport() {
  try {
    const resp = await exportUsersCsv({})
    if (!resp.ok) throw new Error(`导出失败（${resp.status}）`)
    await downloadResponseBlob(resp, 'users_export.csv')
  } catch {
    ElMessage.error('导出失败，请稍后重试')
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
