<template>
  <el-card>
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
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import request from '@/api/request'

const list = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

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

onMounted(() => {
  fetchList()
})
</script>
