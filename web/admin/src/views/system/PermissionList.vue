<template>
  <el-card>
    <div class="hj-toolbar-end">
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
          {{ row.module_label || row.module }}
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
      class="hj-pagination hj-mt-20"
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      @current-change="fetchList"
    />
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { listPermissions } from '@/api/permission'
import type { PermissionItem } from '@/types/role'

const route = useRoute()

const list = ref<PermissionItem[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const keyword = ref('')

async function fetchList() {
  loading.value = true
  try {
    const res = await listPermissions({
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value.trim() || undefined,
    })
    list.value = res.data.items
    total.value = res.data.total
  } catch {
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
  const q = route.query.keyword
  if (q) keyword.value = String(q)
  fetchList()
})

// 全局搜索跳转携带 keyword 时自动过滤
watch(
  () => route.query.keyword,
  q => {
    if (q) {
      keyword.value = String(q)
      page.value = 1
      fetchList()
    }
  },
)
</script>
