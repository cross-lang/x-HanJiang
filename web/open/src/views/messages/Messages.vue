<template>
  <el-card>
    <div class="hj-flex-between hj-mb-16">
      <h2 class="page-title">站内信</h2>
      <el-button type="primary" icon="Refresh" @click="fetchList">刷新</el-button>
    </div>

    <el-alert type="info" :closable="false" class="hj-mb-16">
      站内信功能为规划中的模块（预留）。当前展示占位结构与接口约定，后端
      <code>GET /api/open/v1/messages</code> 就绪后自动生效。
    </el-alert>

    <el-table :data="list" v-loading="loading" empty-text="暂无消息">
      <el-table-column prop="category" label="类型" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.category === 'system'" type="primary" size="small">系统</el-tag>
          <el-tag v-else-if="row.category === 'audit'" type="warning" size="small">审批</el-tag>
          <el-tag v-else type="info" size="small">通知</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="标题" />
      <el-table-column prop="content" label="内容" show-overflow-tooltip />
      <el-table-column prop="read" label="状态" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.read" type="info" size="small">已读</el-tag>
          <el-tag v-else type="danger" size="small">未读</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="时间" width="170">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
    </el-table>

    <el-pagination
      class="hj-pagination"
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      @current-change="fetchList"
    />
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { formatDateTime } from '@/utils/format'
import { listMessages } from '@/api/messages'
import type { OpenMessage } from '@/types/message'

const list = ref<OpenMessage[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

async function fetchList() {
  loading.value = true
  try {
    const res = await listMessages({ page: page.value, page_size: pageSize.value })
    list.value = res.data.items
    total.value = res.data.total
  } catch {
    // 接口待实现：静默保留空列表，占位提示已由 alert 说明
    list.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

onMounted(fetchList)
</script>

<style scoped>
.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
</style>
