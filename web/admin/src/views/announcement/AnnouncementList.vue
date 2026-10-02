<template>
  <div>
    <el-card>
      <div class="hj-toolbar">
        <el-button type="primary" @click="openCreate">新建公告</el-button>
        <div class="hj-flex hj-gap-8">
          <el-select v-model="filter.status" placeholder="状态" clearable style="width: 130px" @change="fetchList">
            <el-option label="草稿" value="draft" />
            <el-option label="已发布" value="published" />
            <el-option label="已下架" value="unpublished" />
          </el-select>
          <el-select v-model="filter.position" placeholder="位置" clearable style="width: 130px" @change="fetchList">
            <el-option label="首页板块" value="board" />
            <el-option label="首页横幅" value="banner" />
          </el-select>
          <el-input
            v-model="filter.keyword"
            placeholder="搜索标题/正文"
            clearable
            style="width: 200px"
            @keyup.enter="fetchList"
            @clear="fetchList"
          />
          <el-button type="primary" icon="Search" @click="fetchList">搜索</el-button>
        </div>
      </div>

      <el-table :data="items" v-loading="loading" border>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column label="位置" width="110">
          <template #default="{ row }">
            <el-tag :type="row.position === 'banner' ? 'warning' : 'info'">
              {{ row.position === 'banner' ? '首页横幅' : '首页板块' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="格式" width="130">
          <template #default="{ row }">
            <el-tag type="primary" effect="plain">{{ row.content_type === 'richtext' ? '富文本' : 'Markdown' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTag(row as AnnouncementItem)">
              {{ statusText(row as AnnouncementItem) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="有效期" width="240">
          <template #default="{ row }"> {{ fmtTime(row.start_at) }} ~ {{ fmtTime(row.end_at) }} </template>
        </el-table-column>
        <el-table-column prop="operator_name" label="操作人" width="110" />
        <el-table-column label="操作" width="220">
          <template #default="{ row }">
            <el-button size="small" @click="viewDetail(row as AnnouncementItem)">详情</el-button>
            <el-button size="small" @click="openEdit(row as AnnouncementItem)">编辑</el-button>
            <el-button
              v-if="row.status === 'draft' || row.status === 'unpublished'"
              size="small"
              type="success"
              link
              @click="publish(row as AnnouncementItem)"
              >发布</el-button
            >
            <el-button
              v-if="row.status === 'published'"
              size="small"
              type="warning"
              link
              @click="unpublish(row as AnnouncementItem)"
              >下架</el-button
            >
            <el-button size="small" type="danger" link @click="remove(row as AnnouncementItem)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        class="hj-pagination hj-mt-12"
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="fetchList"
      />
    </el-card>

    <AnnouncementFormDialog
      v-model:visible="editVisible"
      :mode="isEdit ? 'edit' : 'create'"
      :record="editRecord"
      @submitted="onDialogSubmitted"
    />

    <el-dialog v-model="detailVisible" title="公告详情" width="720px">
      <template v-if="detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="标题">{{ detail.title }}</el-descriptions-item>
          <el-descriptions-item label="展示位置">
            <el-tag :type="detail.position === 'banner' ? 'warning' : 'info'">
              {{ detail.position === 'banner' ? '首页横幅' : '首页板块' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="格式">
            <el-tag type="primary" effect="plain">{{
              detail.content_type === 'richtext' ? '富文本' : 'Markdown'
            }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTag(detail)">{{ statusText(detail) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="有效期">
            {{ fmtTime(detail.start_at) }} ~ {{ fmtTime(detail.end_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="发布人">{{ detail.operator_name || '-' }}</el-descriptions-item>
          <el-descriptions-item v-if="detail.published_at" label="发布时间">{{
            fmtTime(detail.published_at)
          }}</el-descriptions-item>
          <el-descriptions-item label="正文">
            <div class="announcement-preview" v-html="renderAnnouncement(detail.content, detail.content_type)" />
          </el-descriptions-item>
        </el-descriptions>
      </template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { renderAnnouncement } from '@/utils/announcement'
import { formatDateTimeShort } from '@/utils/format'
import {
  listAnnouncements,
  getAnnouncement,
  publishAnnouncement,
  unpublishAnnouncement,
  deleteAnnouncement,
} from '@/api/announcement'
import type { AnnouncementItem } from '@/types/announcement'
import AnnouncementFormDialog from './components/AnnouncementFormDialog.vue'

const items = ref<AnnouncementItem[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const filter = ref<{ status: string; position: string; keyword: string }>({ status: '', position: '', keyword: '' })

const editVisible = ref(false)
const isEdit = ref(false)
const editRecord = ref<AnnouncementItem | null>(null)

const detailVisible = ref(false)
const detail = ref<AnnouncementItem | null>(null)

function fmtTime(v: string | null | undefined): string {
  return formatDateTimeShort(v)
}

function statusText(row: AnnouncementItem): string {
  if (row.status === 'published') return row.is_expired ? '已过期' : '已发布'
  if (row.status === 'draft') return '草稿'
  return '已下架'
}

function statusTag(row: AnnouncementItem) {
  if (row.status === 'published') return row.is_expired ? 'danger' : 'success'
  if (row.status === 'draft') return 'info'
  return 'warning'
}

async function fetchList() {
  loading.value = true
  try {
    const res = await listAnnouncements({
      page: page.value,
      page_size: pageSize.value,
      status: filter.value.status || undefined,
      position: filter.value.position || undefined,
      keyword: filter.value.keyword || undefined,
    })
    items.value = res.data.items
    total.value = res.data.total
  } catch {
    /* 拦截器已处理 */
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEdit.value = false
  editRecord.value = null
  editVisible.value = true
}

function openEdit(row: AnnouncementItem) {
  isEdit.value = true
  editRecord.value = row
  editVisible.value = true
}

/** 表单保存成功：关闭并刷新列表 */
function onDialogSubmitted() {
  editVisible.value = false
  fetchList()
}

async function publish(row: AnnouncementItem) {
  try {
    await publishAnnouncement(row.id)
    ElMessage.success('已发布')
    fetchList()
  } catch {
    /* 拦截器已处理 */
  }
}

async function unpublish(row: AnnouncementItem) {
  try {
    await ElMessageBox.confirm(`确认下架公告「${row.title}」？下架后首页不再展示。`, '下架确认', {
      type: 'warning',
      confirmButtonText: '下架',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await unpublishAnnouncement(row.id)
    ElMessage.success('已下架')
    fetchList()
  } catch {
    /* 拦截器已处理 */
  }
}

async function remove(row: AnnouncementItem) {
  try {
    await ElMessageBox.confirm(`确认删除公告「${row.title}」？删除后不可恢复。`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deleteAnnouncement(row.id)
    ElMessage.success('已删除')
    fetchList()
  } catch {
    /* 拦截器已处理 */
  }
}

async function viewDetail(row: AnnouncementItem) {
  try {
    const res = await getAnnouncement(row.id)
    detail.value = res.data
    detailVisible.value = true
  } catch {
    /* 拦截器已处理 */
  }
}

onMounted(fetchList)
</script>
<style scoped>
.announcement-preview {
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  padding: 12px;
  max-height: 300px;
  overflow: auto;
  line-height: 1.6;
}
.announcement-preview :deep(h1),
.announcement-preview :deep(h2),
.announcement-preview :deep(h3) {
  margin: 8px 0;
}
.announcement-preview :deep(p) {
  margin: 6px 0;
}
.announcement-preview :deep(code) {
  background: #f5f5f5;
  padding: 2px 4px;
  border-radius: 3px;
}
.announcement-preview :deep(pre) {
  background: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
  overflow: auto;
}
</style>
