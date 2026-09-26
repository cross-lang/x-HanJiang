<template>
  <el-card>
    <div style="margin-bottom: 20px">
      <el-button type="primary" @click="handleCreate">新建应用</el-button>
    </div>
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="app_id" label="App ID" width="200" />
      <el-table-column prop="name" label="应用名称" />
      <el-table-column prop="auth_mode" label="鉴权模式" width="90">
        <template #default="{ row }">
          <el-tag :type="row.auth_mode === 'hmac' ? 'success' : 'warning'">{{ row.auth_mode }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="scopes" label="权限范围">
        <template #default="{ row }">
          <el-tag v-for="s in row.scopes" :key="s" size="small" style="margin-right: 4px">{{ s }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'danger'">{{ row.status === 'active' ? '启用' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160" />
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="handleEdit(row)">编辑</el-button>
          <el-button size="small" :type="row.status === 'active' ? 'warning' : 'success'" @click="handleToggleStatus(row)">
            {{ row.status === 'active' ? '禁用' : '启用' }}
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
  <el-dialog v-model="dialogVisible" title="新建应用" width="560px">
    <el-form :model="form" label-width="80px">
      <el-form-item label="名称">
        <el-input v-model="form.name" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="form.description" type="textarea" />
      </el-form-item>
      <el-form-item label="鉴权模式">
        <el-select v-model="form.auth_mode" style="width: 100%">
          <el-option label="明文 (plain)" value="plain" />
          <el-option label="HMAC 签名 (hmac)" value="hmac" />
          <el-option label="双模式 (both)" value="both" />
        </el-select>
      </el-form-item>
      <el-form-item label="权限范围">
        <el-checkbox-group v-model="form.scopes">
          <el-checkbox :model-value="isGroupAll('basic', form.scopes)" :indeterminate="isGroupIndeterminate('basic', form.scopes)" @change="(val: any) => toggleGroup('basic', form.scopes, val)">
            <span style="font-weight: 600; color: #606266;">基础接口</span>
          </el-checkbox>
          <div style="margin-bottom: 12px; margin-left: 24px;">
            <el-checkbox value="health:read" style="margin-right: 20px;">健康检查</el-checkbox>
            <el-checkbox value="app:read">应用信息</el-checkbox>
          </div>
          <el-checkbox :model-value="isGroupAll('user', form.scopes)" :indeterminate="isGroupIndeterminate('user', form.scopes)" @change="(val: any) => toggleGroup('user', form.scopes, val)">
            <span style="font-weight: 600; color: #606266;">用户管理</span>
          </el-checkbox>
          <div style="margin-left: 24px;">
            <el-checkbox value="user:read" style="margin-right: 20px;">查看用户</el-checkbox>
            <el-checkbox value="user:write">写用户</el-checkbox>
          </div>
        </el-checkbox-group>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleSubmit">确定</el-button>
    </template>
  </el-dialog>

  <!-- 编辑弹窗 -->
  <el-dialog v-model="editDialogVisible" title="编辑应用" width="560px">
    <el-form :model="editForm" label-width="80px">
      <el-form-item label="名称">
        <el-input v-model="editForm.name" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="editForm.description" type="textarea" />
      </el-form-item>
      <el-form-item label="鉴权模式">
        <el-select v-model="editForm.auth_mode" style="width: 100%">
          <el-option label="明文 (plain)" value="plain" />
          <el-option label="HMAC 签名 (hmac)" value="hmac" />
          <el-option label="双模式 (both)" value="both" />
        </el-select>
      </el-form-item>
      <el-form-item label="权限范围">
        <el-checkbox-group v-model="editForm.scopes">
          <el-checkbox :model-value="isGroupAll('basic', editForm.scopes)" :indeterminate="isGroupIndeterminate('basic', editForm.scopes)" @change="(val: any) => toggleGroup('basic', editForm.scopes, val)">
            <span style="font-weight: 600; color: #606266;">基础接口</span>
          </el-checkbox>
          <div style="margin-bottom: 12px; margin-left: 24px;">
            <el-checkbox value="health:read" style="margin-right: 20px;">健康检查</el-checkbox>
            <el-checkbox value="app:read">应用信息</el-checkbox>
          </div>
          <el-checkbox :model-value="isGroupAll('user', editForm.scopes)" :indeterminate="isGroupIndeterminate('user', editForm.scopes)" @change="(val: any) => toggleGroup('user', editForm.scopes, val)">
            <span style="font-weight: 600; color: #606266;">用户管理</span>
          </el-checkbox>
          <div style="margin-left: 24px;">
            <el-checkbox value="user:read" style="margin-right: 20px;">查看用户</el-checkbox>
            <el-checkbox value="user:write">写用户</el-checkbox>
          </div>
        </el-checkbox-group>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editDialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleUpdate">确定</el-button>
    </template>
  </el-dialog>

  <!-- 创建成功弹窗 -->
  <el-dialog v-model="resultVisible" title="应用创建成功">
    <el-alert type="success" :closable="false" style="margin-bottom: 16px">
      请妥善保存 App Key，关闭后将无法再次查看！
    </el-alert>
    <p style="display:flex;align-items:center;gap:8px;">
      <strong>App ID：</strong><span>{{ createdApp.app_id }}</span>
      <el-button size="small" @click="copyText(createdApp.app_id)">复制</el-button>
    </p>
    <p style="display:flex;align-items:center;gap:8px;">
      <strong>App Key：</strong><span>{{ createdApp.app_key }}</span>
      <el-button size="small" @click="copyText(createdApp.app_key)">复制</el-button>
    </p>
    <template #footer>
      <el-button type="primary" @click="resultVisible = false">我已保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/api/request'

const list = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const dialogVisible = ref(false)
const resultVisible = ref(false)
const form = ref({ name: '', description: '', auth_mode: 'plain', scopes: [] as string[] })
const createdApp = ref({ app_id: '', app_key: '' })

const editDialogVisible = ref(false)
const editForm = ref({ id: 0, name: '', description: '', auth_mode: 'plain', scopes: [] as string[] })

const SCOPE_GROUPS: Record<string, string[]> = {
  basic: ['health:read', 'app:read'],
  user: ['user:read', 'user:write'],
}

function isGroupAll(group: string, selected: string[]): boolean {
  return SCOPE_GROUPS[group].every(s => selected.includes(s))
}

function isGroupIndeterminate(group: string, selected: string[]): boolean {
  const checked = SCOPE_GROUPS[group].filter(s => selected.includes(s)).length
  return checked > 0 && checked < SCOPE_GROUPS[group].length
}

function toggleGroup(group: string, selected: string[], val: any) {
  if (val) {
    for (const s of SCOPE_GROUPS[group]) {
      if (!selected.includes(s)) selected.push(s)
    }
  } else {
    for (const s of SCOPE_GROUPS[group]) {
      const idx = selected.indexOf(s)
      if (idx > -1) selected.splice(idx, 1)
    }
  }
}

function copyText(text: string) {
  navigator.clipboard.writeText(text).then(() => ElMessage.success('已复制'))
}

async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/admin/apps', { params: { page: page.value, page_size: pageSize.value } })
    list.value = res.data
    total.value = res.data.length
  } catch (e) {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

function handleCreate() {
  form.value = { name: '', description: '', auth_mode: 'plain', scopes: [] }
  dialogVisible.value = true
}

async function handleSubmit() {
  try {
    const res = await request.post('/admin/apps', form.value)
    createdApp.value = res.data
    dialogVisible.value = false
    resultVisible.value = true
    fetchList()
  } catch (e) {
    // 错误已处理
  }
}

function handleEdit(row: any) {
  editForm.value = { id: row.id, name: row.name, description: row.description || '', auth_mode: row.auth_mode, scopes: [...row.scopes] }
  editDialogVisible.value = true
}

async function handleUpdate() {
  try {
    await request.patch(`/admin/apps/${editForm.value.id}`, {
      name: editForm.value.name,
      description: editForm.value.description,
      auth_mode: editForm.value.auth_mode,
      scopes: editForm.value.scopes,
    })
    ElMessage.success('更新成功')
    editDialogVisible.value = false
    fetchList()
  } catch (e) {
    // 错误已处理
  }
}

async function handleToggleStatus(row: any) {
  const newStatus = row.status === 'active' ? 'disabled' : 'active'
  try {
    await ElMessageBox.confirm(
      `确定${newStatus === 'active' ? '启用' : '禁用'}应用「${row.name}」吗？`,
      '危险操作确认',
      { type: 'warning' }
    )
  } catch { return }
  try {
    await request.patch(`/admin/apps/${row.id}`, { status: newStatus })
    ElMessage.success(newStatus === 'active' ? '已启用' : '已禁用')
    fetchList()
  } catch (e) {
    // 错误已处理
  }
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(
      `确定删除应用「${row.name}」吗？删除后该应用将无法调用任何接口，此操作不可撤销！`,
      '危险操作确认',
      { type: 'error', confirmButtonText: '确定删除' }
    )
  } catch { return }
  try {
    await request.delete(`/admin/apps/${row.id}`)
    ElMessage.success('删除成功')
    fetchList()
  } catch (e) {
    // 错误已处理
  }
}

onMounted(() => {
  fetchList()
})
</script>
