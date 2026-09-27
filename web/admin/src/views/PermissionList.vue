<template>
  <el-card>
    <div style="margin-bottom: 16px; display: flex; justify-content: flex-end; align-items: center; gap: 8px">
      <el-input
        v-model="keyword"
        placeholder="按权限编码/名称/模块搜索"
        style="width: 260px"
        clearable
        @keyup.enter="handleSearch"
        @clear="handleSearch"
      />
      <el-button type="primary" icon="Search" @click="handleSearch">搜索</el-button>
    </div>
    <el-table :data="list" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="perm_code" label="权限编码" width="200" />
      <el-table-column prop="perm_name" label="权限名称" width="150" />
      <el-table-column prop="module" label="模块" width="110">
        <template #default="{ row }">
          {{ moduleNameMap[row.module] || row.module }}
        </template>
      </el-table-column>
      <el-table-column prop="operation" label="操作" width="100" />
      <el-table-column prop="description" label="描述" />
      <el-table-column prop="is_deprecated" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_deprecated ? 'danger' : 'success'">
            {{ row.is_deprecated ? '已废弃' : '正常' }}
          </el-tag>
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
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import request from '@/api/request'

const list = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const keyword = ref('')

// 权限模块编码 → 中文名称
const moduleNameMap: Record<string, string> = {
  user: '用户管理',
  role: '角色管理',
  file: '文件管理',
  audit_log: '审计日志',
  login_log: '登录日志',
  notification: '通知管理',
  alert: '告警管理',
  maintenance: '维护管理',
  openapi_app: '开放平台应用',
  openapi_scope: '开放平台权限',
  dashboard: '仪表盘',
  swagger: 'Swagger文档',
}

async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/permissions', {
      params: {
        page: page.value,
        page_size: pageSize.value,
        keyword: keyword.value.trim() || undefined,
      },
    })
    list.value = res.data.items
    total.value = res.data.total
  } catch (e) {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  fetchList()
}

onMounted(() => {
  fetchList()
})
</script>
