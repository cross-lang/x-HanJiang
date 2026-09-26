<template>
  <el-card>
    <div style="margin-bottom: 20px">
      <el-button type="primary" @click="handleCreate">新建用户</el-button>
    </div>
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="name" label="姓名" />
      <el-table-column prop="email" label="邮箱" />
      <el-table-column prop="phone" label="手机号" width="130" />
      <el-table-column prop="role_name" label="角色" width="120" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'danger'">
            {{ row.status === 'active' ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" />
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <template v-if="canOperate(row)">
            <el-button
              v-if="row.status !== 'active'"
              size="small"
              type="success"
              @click="handleToggleStatus(row, 'active')"
            >启用</el-button>
            <el-button
              v-if="row.status === 'active'"
              size="small"
              type="warning"
              @click="handleToggleStatus(row, 'disabled')"
            >禁用</el-button>
            <el-button v-if="row.id !== userStore.userInfo?.id" size="small" @click="handleResetPassword(row)">重置密码</el-button>
          </template>
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

  <el-dialog v-model="dialogVisible" title="新建用户" width="500px">
    <el-form :model="form" label-width="80px">
      <el-form-item label="用户名">
        <el-input v-model="form.username" />
      </el-form-item>
      <el-form-item label="姓名">
        <el-input v-model="form.name" />
      </el-form-item>
      <el-form-item label="邮箱">
        <el-input v-model="form.email" />
      </el-form-item>
      <el-form-item label="手机号">
        <el-input v-model="form.phone" />
      </el-form-item>
      <el-form-item label="生日">
        <el-date-picker v-model="form.birthday" type="date" placeholder="选择生日" />
      </el-form-item>
      <el-form-item label="性别">
        <el-radio-group v-model="form.gender">
          <el-radio value="male">男</el-radio>
          <el-radio value="female">女</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="角色">
        <el-select v-model="form.role_id" style="width: 100%">
          <el-option
            v-for="r in roles"
            :key="r.id"
            :label="r.role_name"
            :value="r.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="密码">
        <el-input v-model="form.password" type="password" show-password />
      </el-form-item>
      <el-form-item label="状态">
        <el-radio-group v-model="form.status">
          <el-radio value="active">启用</el-radio>
          <el-radio value="disabled">禁用</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleSubmit">确定</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="resetVisible" title="重置密码">
    <p style="margin-bottom: 15px">重置用户 <strong>{{ resetUser.username }}</strong> 的密码</p>
    <el-input v-model="resetPassword" type="password" placeholder="请输入新密码" show-password />
    <template #footer>
      <el-button @click="resetVisible = false">取消</el-button>
      <el-button type="primary" @click="confirmResetPassword">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/api/request'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const list = ref<any[]>([])
const roles = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const dialogVisible = ref(false)
const form = ref({
  username: '',
  name: '',
  email: '',
  phone: '',
  birthday: '',
  gender: 'male',
  role_id: null as number | null,
  password: '',
  status: 'active',
})

const resetVisible = ref(false)
const resetUser = ref<any>({})
const resetPassword = ref('')

async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/users', { params: { page: page.value, page_size: pageSize.value } })
    list.value = res.data.items
    total.value = res.data.total
  } catch (e) {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

async function fetchRoles() {
  try {
    const res = await request.get('/roles')
    roles.value = res.data.items || res.data || []
    const adminRole = roles.value.find((r: any) => r.role_code === 'admin')
    if (adminRole) form.value.role_id = adminRole.id
  } catch (e) {
    // 错误已处理
  }
}

function handleCreate() {
  form.value = {
    username: '',
    name: '',
    email: '',
    phone: '',
    birthday: '',
    gender: 'male',
    role_id: null,
    password: '',
    status: 'active',
  }
  fetchRoles()
  dialogVisible.value = true
}

async function handleSubmit() {
  try {
    await request.post('/users', form.value)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    fetchList()
  } catch (e) {
    // 错误已处理
  }
}

async function handleToggleStatus(row: any, status: string) {
  const action = status === 'active' ? '启用' : '禁用'
  try {
    await ElMessageBox.confirm(`确定要${action}用户 ${row.username} 吗？`, '提示', { type: 'warning' })
    await request.patch(`/users/${row.id}`, { status })
    ElMessage.success(`${action}成功`)
    fetchList()
  } catch (e) {
    // 取消或错误
  }
}

function handleResetPassword(row: any) {
  resetUser.value = row
  resetVisible.value = true
}

async function confirmResetPassword() {
  try {
    await request.post(`/users/${resetUser.value.id}/reset-password`, { new_password: resetPassword.value, confirm_password: resetPassword.value })
    ElMessage.success('密码已重置')
    resetVisible.value = false
  } catch (e) {
    // 错误已处理
  }
}

function canOperate(row: any): boolean {
  // 超级管理员才能操作超级管理员
  if (row.username === 'superadmin') {
    return userStore.userInfo?.username === 'superadmin'
  }
  return true
}

onMounted(() => {
  fetchList()
})
</script>
