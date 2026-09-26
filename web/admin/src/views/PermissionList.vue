<template>
  <el-card>
    <div style="margin-bottom: 20px">
      <el-button type="primary" @click="handleCreate">新建权限</el-button>
    </div>
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="perm_code" label="权限编码" width="200" />
      <el-table-column prop="perm_name" label="权限名称" />
      <el-table-column prop="module" label="模块" width="100" />
      <el-table-column prop="operation" label="操作" width="100" />
      <el-table-column prop="description" label="描述" />
    </el-table>
    <el-pagination
      style="margin-top: 20px; justify-content: flex-end; display: flex"
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      @current-change="fetchList"
    />
  </el-card>

  <el-dialog v-model="dialogVisible" title="新建权限">
    <el-form :model="form" label-width="80px">
      <el-form-item label="编码">
        <el-input v-model="form.perm_code" placeholder="如 user:create" />
      </el-form-item>
      <el-form-item label="名称">
        <el-input v-model="form.perm_name" />
      </el-form-item>
      <el-form-item label="模块">
        <el-input v-model="form.module" placeholder="如 user" />
      </el-form-item>
      <el-form-item label="操作">
        <el-input v-model="form.operation" placeholder="如 create" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="form.description" type="textarea" />
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
const form = ref({ perm_code: '', perm_name: '', module: '', operation: '', description: '' })

async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/permissions', { params: { page: page.value, page_size: pageSize.value } })
    list.value = res.data.items
    total.value = res.data.total
  } catch (e) {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

function handleCreate() {
  form.value = { perm_code: '', perm_name: '', module: '', operation: '', description: '' }
  dialogVisible.value = true
}

async function handleSubmit() {
  try {
    await request.post('/permissions', form.value)
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
