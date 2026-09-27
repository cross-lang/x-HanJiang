<template>
  <el-card>
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="scope_code" label="Scope 编码" width="220" />
      <el-table-column prop="scope_name" label="Scope 名称" />
      <el-table-column prop="module_label" label="模块" width="120">
        <template #default="{ row }">
          <el-tag size="small">{{ row.module_label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="operation" label="操作" width="100">
        <template #default="{ row }">
          <el-tag :type="operationType(row.operation)" size="small">{{ row.operation }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import request from '@/api/request'

const list = ref<any[]>([])
const loading = ref(false)

function operationType(op: string) {
  const map: Record<string, string> = {
    read: 'success',
    write: 'warning',
    delete: 'danger',
  }
  return map[op] || 'info'
}

onMounted(async () => {
  loading.value = true
  try {
    const res = await request.get('/admin/apps/scopes')
    list.value = res.data
  } catch (e) {
    // 错误已处理
  } finally {
    loading.value = false
  }
})
</script>
