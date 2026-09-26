<template>
  <el-card>
    <el-table :data="list" v-loading="loading">
      <template v-if="isLoginLog">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="login_type" label="登录方式" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP" width="140" />
        <el-table-column prop="created_at" label="时间" width="180" />
      </template>
      <template v-else>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="operator_name" label="操作人" width="120" />
        <el-table-column prop="entity_type" label="实体类型" width="120" />
        <el-table-column prop="action" label="操作" width="100" />
        <el-table-column prop="remarks" label="备注" show-overflow-tooltip />
        <el-table-column prop="ip_address" label="IP" width="140" />
        <el-table-column prop="created_at" label="时间" width="180" />
      </template>
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
import { ref, onMounted, computed, watch } from 'vue'
import request from '@/api/request'

const props = defineProps<{ logType?: string }>()
const isLoginLog = computed(() => props.logType === 'login')

const list = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

async function fetchList() {
  loading.value = true
  try {
    const url = isLoginLog.value ? '/audit/login-logs' : '/audit/logs'
    const res = await request.get(url, { params: { page: page.value, page_size: pageSize.value } })
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

watch(() => props.logType, () => {
  page.value = 1
  fetchList()
})
</script>
