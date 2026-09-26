<template>
  <el-card>
    <div style="margin-bottom: 20px">
      <el-button type="primary" @click="handleCreate">新建应用</el-button>
    </div>
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="app_id" label="App ID" width="280" />
      <el-table-column prop="name" label="应用名称" />
      <el-table-column prop="auth_mode" label="鉴权模式" width="100">
        <template #default="{ row }">
          <el-tag :type="row.auth_mode === 'hmac' ? 'success' : 'warning'">
            {{ row.auth_mode }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="scopes" label="权限范围" />
      <el-table-column prop="created_at" label="创建时间" width="180" />
    </el-table>
    <el-pagination
      style="margin-top: 20px; justify-content: flex-end; display: flex"
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      @current-change="fetchList"
    />
  </el-card>

  <el-dialog v-model="dialogVisible" title="新建应用">
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
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="handleSubmit">确定</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="resultVisible" title="应用创建成功">
    <el-alert type="success" :closable="false" style="margin-bottom: 16px">
      请妥善保存 App Key，关闭后将无法再次查看！
    </el-alert>
    <p><strong>App ID：</strong>{{ createdApp.app_id }}</p>
    <p><strong>App Key：</strong>{{ createdApp.app_key }}</p>
    <template #footer>
      <el-button type="primary" @click="resultVisible = false">我已保存</el-button>
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
const resultVisible = ref(false)
const form = ref({ name: '', description: '', auth_mode: 'plain' })
const createdApp = ref({ app_id: '', app_key: '' })

async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/admin/apps', { params: { page: page.value, page_size: pageSize.value } })
    list.value = res.data.items
    total.value = res.data.total
  } catch (e) {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

function handleCreate() {
  form.value = { name: '', description: '', auth_mode: 'plain' }
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

onMounted(() => {
  fetchList()
})
</script>
