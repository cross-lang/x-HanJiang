<template>
  <el-card>
    <div class="hj-toolbar-end">
      <el-input
        v-model="keyword"
        placeholder="按Scope编码/名称/模块搜索"
        style="width: 260px"
        clearable
        @keyup.enter="handleSearch"
        @clear="handleSearch"
      />
      <el-button type="primary" icon="Search" @click="handleSearch">搜索</el-button>
    </div>
    <el-table :data="filteredList" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="scope_code" label="Scope 编码" width="220" />
      <el-table-column prop="scope_name" label="Scope 名称" />
      <el-table-column prop="module_label" label="模块" width="120">
        <template #default="{ row }">
          <el-tag size="small">{{ row.module_label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="operation" label="操作" width="110">
        <template #default="{ row }">
          <el-tag :type="operationType(row.operation)" size="small">{{ operationLabel(row.operation) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" />
    </el-table>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useScopeCatalog } from '@/composables/useScopeCatalog'

const { scopeList, fetchScopes } = useScopeCatalog()
const loading = ref(false)
const keyword = ref('')

const filteredList = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return scopeList.value
  return scopeList.value.filter(row =>
    [row.scope_code, row.scope_name, row.module_label, row.module, row.operation, row.description]
      .filter(Boolean)
      .some(v => String(v).toLowerCase().includes(kw)),
  )
})

function handleSearch() {
  // 前端过滤即时生效，无需重新请求
}

function operationType(op: string): 'primary' | 'success' | 'warning' | 'info' | 'danger' {
  const map: Record<string, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = {
    read: 'success',
    write: 'warning',
    delete: 'danger',
  }
  return map[op] || 'info'
}

/** 操作动作中文标签（read/write 为开放平台 scope 动作词表） */
function operationLabel(op: string): string {
  const map: Record<string, string> = { read: '读（read）', write: '写（write）' }
  return map[op] || op
}

onMounted(async () => {
  loading.value = true
  try {
    await fetchScopes()
  } catch {
    // 错误已处理
  } finally {
    loading.value = false
  }
})
</script>
