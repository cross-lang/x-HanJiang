<template>
  <el-card>
    <div class="hj-toolbar">
      <el-button type="primary" @click="handleCreate">新建角色</el-button>
      <div class="hj-flex hj-gap-8">
        <el-input
          v-model="keyword"
          placeholder="按角色名称/编码搜索"
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
      <el-table-column prop="role_name" label="角色名称" />
      <el-table-column prop="role_code" label="角色编码" />
      <el-table-column prop="role_type" label="角色类型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.role_type === 'system' ? 'warning' : 'info'" effect="plain" size="small">
            {{ row.role_type === 'system' ? '系统内置' : '自定义' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'enabled' ? 'success' : 'danger'" effect="plain" size="small">
            {{ row.status === 'enabled' ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="250" fixed="right">
        <template #default="{ row }">
          <!-- 系统内置角色（superadmin/admin/user）不允许编辑、禁用、删除 -->
          <template v-if="row.role_type !== 'system'">
            <el-button size="small" @click="handleEdit(row as RoleItem)">编辑</el-button>
            <el-button size="small" @click="handleToggleStatus(row as RoleItem)">
              {{ row.status === 'enabled' ? '禁用' : '启用' }}
            </el-button>
            <el-button size="small" type="danger" @click="handleDelete(row as RoleItem)">删除</el-button>
          </template>
          <span v-else class="hj-text-muted">系统内置</span>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      class="hj-pagination hj-mt-20"
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      @current-change="fetchList"
    />
  </el-card>

  <RoleFormDialog v-model:visible="dialogVisible" mode="create" @submitted="onDialogSubmitted" />
  <RoleFormDialog v-model:visible="editDialogVisible" mode="edit" :record="editRecord" @submitted="onDialogSubmitted" />
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDateTime } from '@/utils/format'
import { listRoles, updateRole, deleteRole } from '@/api/role'
import type { RoleItem } from '@/types/role'
import RoleFormDialog from './components/RoleFormDialog.vue'

const route = useRoute()

const list = ref<RoleItem[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const keyword = ref('')

// 新建 / 编辑弹窗（表单逻辑下沉至 RoleFormDialog）
const dialogVisible = ref(false)
const editDialogVisible = ref(false)
const editRecord = ref<RoleItem | null>(null)

async function fetchList() {
  loading.value = true
  try {
    const res = await listRoles({
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value.trim() || undefined,
    })
    // 兼容后端两种返回：分页包裹或纯数组
    list.value = Array.isArray(res.data) ? res.data : res.data.items
    total.value = Array.isArray(res.data) ? res.data.length : res.data.total
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

function handleCreate() {
  dialogVisible.value = true
}

function handleEdit(row: RoleItem) {
  editRecord.value = row
  editDialogVisible.value = true
}

/** 弹窗提交成功：关闭并刷新列表 */
function onDialogSubmitted() {
  dialogVisible.value = false
  editDialogVisible.value = false
  fetchList()
}

async function handleToggleStatus(row: RoleItem) {
  const newStatus = row.status === 'enabled' ? 'disabled' : 'enabled'
  try {
    await updateRole(row.id, { status: newStatus })
    ElMessage.success(newStatus === 'enabled' ? '已启用' : '已禁用')
    fetchList()
  } catch {
    // 错误已处理
  }
}

async function handleDelete(row: RoleItem) {
  try {
    await ElMessageBox.confirm(`确定删除角色「${row.role_name}」吗？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteRole(row.id)
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
