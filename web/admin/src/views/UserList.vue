<template>
  <el-card>
    <div style="margin-bottom: 20px">
      <el-button type="primary" @click="handleCreate">新建用户</el-button>
    </div>
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="email" label="邮箱" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'danger'">
            {{ row.status === 1 ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" />
    </el-table>
    <el-pagination
      style="margin-top: 20px; justify-content: flex-end; display: flex"
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      @current-change="fetchList"
    />
  </el-card>

  <el-dialog v-model="dialogVisible" title="新建用户">
    <el-form :model="form" label-width="80px">
      <el-form-item label="用户名">
        <el-input v-model="form.username" />
      </el-form-item>
      <el-form-item label="邮箱">
        <el-input v-model="form.email" />
      </el-form-item>
      <el-form-item label="密码">
        <el-input v-model="form.password" type="password" show-password />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleSubmit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/request'

const list = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const dialogVisible = ref(false)
const form = ref({ username: '', email: '', password: '' })

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

function handleCreate() {
  form.value = { username: '', email: '', password: '' }
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

onMounted(() => {
  fetchList()
})
</script>
