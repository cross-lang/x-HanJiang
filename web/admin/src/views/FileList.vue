<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <el-upload :show-file-list="false" :http-request="handleUpload" :headers="uploadHeaders">
        <el-button type="primary" icon="Upload">上传文件</el-button>
      </el-upload>
      <div style="display: flex; gap: 8px">
        <el-input v-model="keyword" placeholder="按文件名搜索" style="width: 240px" clearable @keyup.enter="handleSearch" @clear="handleSearch" />
        <el-button type="primary" icon="Search" @click="handleSearch">搜索</el-button>
      </div>
    </div>

    <el-table :data="list" v-loading="loading" border>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="original_name" label="文件名" min-width="200" show-overflow-tooltip />
      <el-table-column prop="folder" label="目录" width="120" />
      <el-table-column label="大小" width="120">
        <template #default="{ row }">{{ formatSize(row.size_bytes) }}</template>
      </el-table-column>
      <el-table-column prop="uploader_display" label="上传者" min-width="150" />
      <el-table-column label="上传时间" width="180">
        <template #default="{ row }">{{ row.created_at ? row.created_at.replace('T', ' ').substring(0, 19) : '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="handleDownload(row)">下载</el-button>
          <el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      style="margin-top: 16px; justify-content: flex-end; display: flex"
      :current-page="page"
      :page-size="pageSize"
      :total="total"
      layout="total, prev, pager, next"
      @current-change="onPageChange"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/api/request'

const route = useRoute()

const list = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const keyword = ref('')

const uploadHeaders = {
  Authorization: `Bearer ${localStorage.getItem('access_token') || ''}`,
}

async function loadData() {
  loading.value = true
  try {
    const res = await request.get('/files', {
      params: { page: page.value, page_size: pageSize.value, keyword: keyword.value.trim() || undefined },
    })
    list.value = res.data.items || []
    total.value = res.data.total || 0
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadData()
}

async function handleUpload(option: any) {
  const formData = new FormData()
  formData.append('file', option.file)
  try {
    await request.post('/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    ElMessage.success('上传成功')
    loadData()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '上传失败')
  }
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除文件 "${row.original_name}" 吗？`, '提示', { type: 'warning' })
    await request.delete(`/files/${row.id}`)
    ElMessage.success('删除成功')
    loadData()
  } catch { /* cancelled */ }
}

function handleDownload(row: any) {
  const token = localStorage.getItem('access_token') || ''
  // row.url 形如 /files/general/xxx.pdf，去掉 /files/ 前缀作为存储 key
  const key = row.url.replace(/^\/files\//, '')
  fetch(`/api/v1/files/${key}`, { headers: { Authorization: `Bearer ${token}` } })
    .then(r => r.blob())
    .then(blob => {
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = row.original_name || 'file'
      link.click()
      URL.revokeObjectURL(url)
    })
}

function onPageChange(p: number) {
  page.value = p
  loadData()
}

function formatSize(bytes: number) {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

onMounted(() => {
  const q = route.query.keyword
  if (q) keyword.value = String(q)
  loadData()
})

// 全局搜索跳转携带 keyword 时自动过滤
watch(() => route.query.keyword, (q) => {
  if (q) {
    keyword.value = String(q)
    page.value = 1
    loadData()
  }
})
</script>
