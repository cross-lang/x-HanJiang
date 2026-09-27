<template>
  <el-card>
    <div style="margin-bottom: 20px">
      <el-button type="primary" @click="handleCreate">新建应用</el-button>
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
  <el-dialog v-model="dialogVisible" title="新建应用" width="640px">
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
        <el-collapse v-model="activeGroups">
          <el-collapse-item v-for="(items, module) in groupedScopes" :key="module" :name="module">
            <template #title>
              <el-checkbox
                :model-value="isGroupAllChecked(items, form.scopes)"
                :indeterminate="isGroupIndeterminate(items, form.scopes)"
                @change="(val: any) => toggleGroup(items, form.scopes, val)"
                @click.stop
              >{{ moduleLabel(module, items) }}</el-checkbox>
            </template>
            <el-checkbox-group v-model="form.scopes">
              <div v-for="s in items" :key="s.id" style="margin-bottom: 8px; margin-left: 10px">
                <el-checkbox :value="s.scope_code">
                  {{ s.scope_name }}（{{ s.scope_code }}）
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
  <el-dialog v-model="editDialogVisible" title="编辑应用" width="640px">
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
        <el-collapse v-model="editActiveGroups">
          <el-collapse-item v-for="(items, module) in groupedScopes" :key="module" :name="module">
            <template #title>
              <el-checkbox
                :model-value="isGroupAllChecked(items, editForm.scopes)"
                :indeterminate="isGroupIndeterminate(items, editForm.scopes)"
                @change="(val: any) => toggleGroup(items, editForm.scopes, val)"
                @click.stop
              >{{ moduleLabel(module, items) }}</el-checkbox>
            </template>
            <el-checkbox-group v-model="editForm.scopes">
              <div v-for="s in items" :key="s.id" style="margin-bottom: 8px; margin-left: 10px">
                <el-checkbox :value="s.scope_code">
                  {{ s.scope_name }}（{{ s.scope_code }}）
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
import { ref, computed, onMounted } from 'vue'
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

const scopeList = ref<any[]>([])
const activeGroups = ref<string[]>([])
const editActiveGroups = ref<string[]>([])

const groupedScopes = computed(() => {
  const groups: Record<string, any[]> = {}
  for (const s of scopeList.value) {
    const mod = s.module || '其他'
    if (!groups[mod]) groups[mod] = []
    groups[mod].push(s)
  }
  return groups
})

function isGroupAllChecked(items: any[], selected: string[]): boolean {
  return items.length > 0 && items.every((s: any) => selected.includes(s.scope_code))
}

function isGroupIndeterminate(items: any[], selected: string[]): boolean {
  const checked = items.filter((s: any) => selected.includes(s.scope_code)).length
  return checked > 0 && checked < items.length
}

function toggleGroup(items: any[], selected: string[], val: any) {
  const codes = items.map((s: any) => s.scope_code)
  if (val) {
    for (const c of codes) {
      if (!selected.includes(c)) selected.push(c)
    }
  } else {
    for (const c of codes) {
      const idx = selected.indexOf(c)
      if (idx > -1) selected.splice(idx, 1)
    }
  }
}

function moduleLabel(mod: string, items: any[]): string {
  return items[0]?.module_label || mod
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

async function fetchScopes() {
  const res = await request.get('/admin/apps/scopes')
  scopeList.value = res.data
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
  fetchScopes()
})
</script>
