<template>
  <el-card>
    <div style="margin-bottom: 20px">
      <el-button type="primary" @click="handleCreate">新建角色</el-button>
    </div>
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="role_name" label="角色名称" />
      <el-table-column prop="role_code" label="角色编码" />
      <el-table-column prop="role_type" label="角色类型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.role_type === 'system' ? 'warning' : 'info'">
            {{ row.role_type === 'system' ? '系统内置' : '自定义' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'enabled' ? 'success' : 'danger'">
            {{ row.status === 'enabled' ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" />
      <el-table-column label="操作" width="250" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="handleEdit(row)">编辑</el-button>
          <el-button size="small" @click="handleToggleStatus(row)">
            {{ row.status === 'enabled' ? '禁用' : '启用' }}
          </el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      style="margin-top: 20px; justify-content: flex-end; display: flex"
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      @current-change="fetchList"
    />
  </el-card>

  <!-- 新建弹窗 -->
  <el-dialog v-model="dialogVisible" title="新建角色" width="600px">
    <el-form :model="form" label-width="80px">
      <el-form-item label="名称">
        <el-input v-model="form.role_name" />
      </el-form-item>
      <el-form-item label="编码">
        <el-input v-model="form.role_code" placeholder="如 auditor" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="form.description" type="textarea" />
      </el-form-item>
      <el-form-item label="权限">
        <el-collapse v-model="activeGroups">
          <el-collapse-item v-for="(items, module) in groupedPermissions" :key="module" :name="module">
            <template #title>
              <el-checkbox
                :model-value="isGroupAllChecked(items, selectedPermissions)"
                :indeterminate="isGroupIndeterminate(items, selectedPermissions)"
                @change="(val: any) => toggleGroup(items, selectedPermissions, val)"
                @click.stop
              >{{ moduleLabel(module, items) }}</el-checkbox>
            </template>
            <el-checkbox-group v-model="selectedPermissions">
              <div v-for="p in items" :key="p.id" style="margin-bottom: 8px; margin-left: 10px">
                <el-checkbox :value="p.id">
                  {{ p.perm_name }}（{{ p.perm_code }}）
                </el-checkbox>
              </div>
            </el-checkbox-group>
          </el-collapse-item>
        </el-collapse>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleSubmit">确定</el-button>
    </template>
  </el-dialog>

  <!-- 编辑弹窗 -->
  <el-dialog v-model="editDialogVisible" title="编辑角色" width="600px">
    <el-form :model="editForm" label-width="80px">
      <el-form-item label="名称">
        <el-input v-model="editForm.role_name" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="editForm.description" type="textarea" />
      </el-form-item>
      <el-form-item label="权限">
        <el-collapse v-model="editActiveGroups">
          <el-collapse-item v-for="(items, module) in groupedPermissions" :key="module" :name="module">
            <template #title>
              <el-checkbox
                :model-value="isGroupAllChecked(items, editSelectedPermissions)"
                :indeterminate="isGroupIndeterminate(items, editSelectedPermissions)"
                @change="(val: any) => toggleGroup(items, editSelectedPermissions, val)"
                @click.stop
              >{{ moduleLabel(module, items) }}</el-checkbox>
            </template>
            <el-checkbox-group v-model="editSelectedPermissions">
              <div v-for="p in items" :key="p.id" style="margin-bottom: 8px; margin-left: 10px">
                <el-checkbox :value="p.id">
                  {{ p.perm_name }}（{{ p.perm_code }}）
                </el-checkbox>
              </div>
            </el-checkbox-group>
          </el-collapse-item>
        </el-collapse>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editDialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleUpdate">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/api/request'

const list = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 新建
const dialogVisible = ref(false)
const form = ref({ role_name: '', role_code: '', description: '' })
const selectedPermissions = ref<number[]>([])
const permissionList = ref<any[]>([])
const activeGroups = ref<string[]>([])
const editActiveGroups = ref<string[]>([])

const groupedPermissions = computed(() => {
  const groups: Record<string, any[]> = {}
  for (const p of permissionList.value) {
    const mod = p.module || '其他'
    if (!groups[mod]) groups[mod] = []
    groups[mod].push(p)
  }
  return groups
})

function isGroupAllChecked(items: any[], selected: number[]): boolean {
  return items.length > 0 && items.every((p: any) => selected.includes(p.id))
}

function isGroupIndeterminate(items: any[], selected: number[]): boolean {
  const checked = items.filter((p: any) => selected.includes(p.id)).length
  return checked > 0 && checked < items.length
}

function toggleGroup(items: any[], selected: number[], val: any) {
  const ids = items.map((p: any) => p.id)
  if (val) {
    for (const id of ids) {
      if (!selected.includes(id)) selected.push(id)
    }
  } else {
    for (const id of ids) {
      const idx = selected.indexOf(id)
      if (idx > -1) selected.splice(idx, 1)
    }
  }
}

function moduleLabel(mod: string, items: any[]): string {
  return items[0]?.module_label || mod
}

// 编辑
const editDialogVisible = ref(false)
const editForm = ref({ id: 0, role_name: '', description: '' })
const editSelectedPermissions = ref<number[]>([])

async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/roles', { params: { page: page.value, page_size: pageSize.value } })
    list.value = res.data.items
    total.value = res.data.total
  } catch (e) {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

async function fetchPermissions() {
  const res = await request.get('/permissions', { params: { page: 1, page_size: 200 } })
  permissionList.value = res.data.items.filter((p: any) => !p.is_deprecated)
}

function handleCreate() {
  form.value = { role_name: '', role_code: '', description: '' }
  selectedPermissions.value = []
  dialogVisible.value = true
}

async function handleSubmit() {
  try {
    const res = await request.post('/roles', form.value)
    const roleId = res.data.id
    for (const permId of selectedPermissions.value) {
      await request.post(`/roles/${roleId}/permissions`, { permission_id: permId })
    }
    ElMessage.success('创建成功')
    dialogVisible.value = false
    fetchList()
  } catch (e) {
    // 错误已处理
  }
}

async function handleEdit(row: any) {
  editForm.value = { id: row.id, role_name: row.role_name, description: row.description || '' }
  // 查角色已有权限
  const res = await request.get(`/roles/${row.id}/permissions`)
  editSelectedPermissions.value = res.data.map((p: any) => p.permission.id)
  editDialogVisible.value = true
}

async function handleUpdate() {
  try {
    // 更新基本信息
    await request.post(`/roles/${editForm.value.id}/update`, {
      role_name: editForm.value.role_name,
      description: editForm.value.description,
    })
    // 对比权限：先解绑不在新列表里的，再绑定新的
    const currentPerms = editSelectedPermissions.value
    const oldRes = await request.get(`/roles/${editForm.value.id}/permissions`)
    const oldPerms = oldRes.data.map((p: any) => p.permission.id)
    // 解绑旧的
    for (const pid of oldPerms) {
      if (!currentPerms.includes(pid)) {
        await request.post(`/roles/${editForm.value.id}/permissions/${pid}/unbind`)
      }
    }
    // 绑定新的
    for (const pid of currentPerms) {
      if (!oldPerms.includes(pid)) {
        await request.post(`/roles/${editForm.value.id}/permissions`, { permission_id: pid })
      }
    }
    ElMessage.success('更新成功')
    editDialogVisible.value = false
    fetchList()
  } catch (e) {
    // 错误已处理
  }
}

async function handleToggleStatus(row: any) {
  const newStatus = row.status === 'enabled' ? 'disabled' : 'enabled'
  try {
    await request.post(`/roles/${row.id}/update`, { status: newStatus })
    ElMessage.success(newStatus === 'enabled' ? '已启用' : '已禁用')
    fetchList()
  } catch (e) {
    // 错误已处理
  }
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除角色「${row.role_name}」吗？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await request.post(`/roles/${row.id}/delete`)
    ElMessage.success('删除成功')
    fetchList()
  } catch (e) {
    // 错误已处理
  }
}

onMounted(() => {
  fetchList()
  fetchPermissions()
})
</script>
