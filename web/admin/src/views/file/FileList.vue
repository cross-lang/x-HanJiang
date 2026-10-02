<template>
  <el-card>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px">
      <el-upload :show-file-list="false" :http-request="handleUpload" :headers="uploadHeaders">
        <el-button type="primary" icon="Upload">上传文件</el-button>
      </el-upload>
      <div style="display: flex; gap: 8px">
        <el-input
          v-model="keyword"
          placeholder="按文件名搜索"
          style="width: 240px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-button type="primary" icon="Search" @click="handleSearch">搜索</el-button>
      </div>
    </div>

    <el-table :data="list" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="original_name" label="文件名" min-width="200" show-overflow-tooltip />
      <el-table-column prop="folder" label="目录" width="120" />
      <el-table-column label="大小" width="120">
        <template #default="{ row }">{{ formatSize((row as FileItem).size_bytes) }}</template>
      </el-table-column>
      <el-table-column prop="uploader_display" label="上传者" min-width="150" />
      <el-table-column label="上传时间" width="180">
        <template #default="{ row }">{{ formatDateTime((row as FileItem).created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="handleDownload(row as FileItem)">下载</el-button>
          <el-button text type="danger" size="small" @click="handleDelete(row as FileItem)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      style="margin-top: 20px; justify-content: flex-end; display: flex"
      :current-page="page"
      :page-size="pageSize"
      :total="total"
      layout="total, prev, pager, next"
      @current-change="onPageChange"
    />
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDateTime } from '@/utils/format'
import { getToken } from '@/utils/storage'
import { downloadResponseBlob } from '@/utils/download'
import { listFiles, uploadFile, deleteFile, downloadFileBlob } from '@/api/file'
import type { FileItem } from '@/types/file'

const route = useRoute()

const list = ref<FileItem[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const keyword = ref('')

const uploadHeaders = {
  Authorization: `Bearer ${getToken() || ''}`,
}

async function loadData() {
  loading.value = true
  try {
    const res = await listFiles({
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value.trim() || undefined,
    })
    list.value = res.data.items
    total.value = res.data.total
  } catch {
    // 错误提示由请求拦截器统一处理
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  loadData()
}

async function handleUpload(option: { file: File }) {
  const formData = new FormData()
  formData.append('file', option.file)
  try {
    await uploadFile(formData)
    ElMessage.success('上传成功')
    loadData()
  } catch {
    // 错误提示由请求拦截器统一处理
  }
}

async function handleDelete(row: FileItem) {
  try {
    await ElMessageBox.confirm(`确定删除文件 "${row.original_name}" 吗？`, '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteFile(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch {
    // 错误已处理
  }
}

async function handleDownload(row: FileItem) {
  try {
    // row.url 形如 /files/general/xxx.pdf，去掉 /files/ 前缀作为存储 key
    const key = row.url.replace(/^\/files\//, '')
    const resp = await downloadFileBlob(key)
    if (!resp.ok) throw new Error(`下载失败（${resp.status}）`)
    await downloadResponseBlob(resp, row.original_name || 'file')
  } catch {
    ElMessage.error('下载失败，请稍后重试')
  }
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
watch(
  () => route.query.keyword,
  q => {
    if (q) {
      keyword.value = String(q)
      page.value = 1
      loadData()
    }
  },
)
</script>
