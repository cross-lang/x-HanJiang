<template>
  <div>
    <el-card>
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px">
        <el-button type="primary" @click="openCreate">新建公告</el-button>
        <div style="display: flex; gap: 8px">
          <el-select v-model="filter.status" placeholder="状态" clearable style="width: 130px" @change="fetchList">
            <el-option label="草稿" value="draft" />
            <el-option label="已发布" value="published" />
            <el-option label="已下架" value="unpublished" />
          </el-select>
          <el-select v-model="filter.position" placeholder="位置" clearable style="width: 130px" @change="fetchList">
            <el-option label="首页板块" value="board" />
            <el-option label="首页横幅" value="banner" />
          </el-select>
          <el-input v-model="filter.keyword" placeholder="搜索标题/正文" clearable style="width: 200px" @keyup.enter="fetchList" @clear="fetchList" />
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
        <el-table-column label="格式" width="100">
          <template #default="{ row }">
            <el-tag type="primary" effect="plain">{{ row.content_type === 'richtext' ? '富文本' : 'Markdown' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTag(row)">
              {{ statusText(row) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="有效期" width="300">
          <template #default="{ row }">
            {{ fmtTime(row.start_at) }} ~ {{ fmtTime(row.end_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="operator_name" label="操作人" width="110" />
        <el-table-column label="操作" width="220">
          <template #default="{ row }">
            <el-button size="small" @click="viewDetail(row)">详情</el-button>
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button
              v-if="row.status === 'draft' || row.status === 'unpublished'"
              size="small"
              type="success"
              link
              @click="publish(row)"
            >发布</el-button>
            <el-button
              v-if="row.status === 'published'"
              size="small"
              type="warning"
              link
              @click="unpublish(row)"
            >下架</el-button>
            <el-button size="small" type="danger" link @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        style="margin-top: 12px; justify-content: flex-end; display: flex"
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="fetchList"
      />
    </el-card>

    <el-dialog v-model="editVisible" :title="isEdit ? '编辑公告' : '新建公告'" width="760px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" maxlength="200" placeholder="公告标题" />
        </el-form-item>
        <el-form-item label="展示位置" required>
          <el-radio-group v-model="form.position">
            <el-radio value="board">首页板块</el-radio>
            <el-radio value="banner">首页横幅</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="正文格式" required>
          <el-radio-group v-model="form.content_type">
            <el-radio value="markdown">Markdown</el-radio>
            <el-radio value="richtext">富文本</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="正文" required>
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="10"
            maxlength="20000"
            :placeholder="form.content_type === 'richtext' ? '输入 HTML 富文本内容' : '支持 Markdown 语法'"
          />
          <div v-if="form.content" style="margin-top: 8px">
            <el-divider content-position="left">预览</el-divider>
            <div class="announcement-preview" v-html="previewHtml" />
          </div>
        </el-form-item>
        <el-form-item label="有效期" required>
          <el-date-picker
            v-model="form.start_at"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="开始时间"
            style="width: 240px; margin-right: 8px"
          />
          <el-date-picker
            v-model="form.end_at"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="结束时间"
            style="width: 240px"
          />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" :max="9999" />
          <span style="color: #999; margin-left: 8px; font-size: 12px">数值越小越靠前</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

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
            <el-tag type="primary" effect="plain">{{ detail.content_type === 'richtext' ? '富文本' : 'Markdown' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTag(detail)">{{ statusText(detail) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="有效期">
            {{ fmtTime(detail.start_at) }} ~ {{ fmtTime(detail.end_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="发布人">{{ detail.operator_name || '-' }}</el-descriptions-item>
          <el-descriptions-item v-if="detail.published_at" label="发布时间">{{ fmtTime(detail.published_at) }}</el-descriptions-item>
          <el-descriptions-item label="正文">
            <div class="announcement-preview" v-html="renderAnnouncement(detail.content, detail.content_type)" />
          </el-descriptions-item>
        </el-descriptions>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/api/request'
import { renderAnnouncement } from '@/utils/announcement'

const items = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const filter = ref<any>({ status: '', position: '', keyword: '' })

const editVisible = ref(false)
const isEdit = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const form = ref<any>({
  title: '',
  content: '',
  content_type: 'markdown',
  position: 'board',
  start_at: '',
  end_at: '',
  sort_order: 0,
})

const detailVisible = ref(false)
const detail = ref<any>(null)

const previewHtml = computed(() => renderAnnouncement(form.value.content || '', form.value.content_type))

function fmtTime(v: string | null | undefined): string {
  if (!v) return ''
  return v.replace('T', ' ').slice(0, 16)
}

function statusText(row: any): string {
  if (row.status === 'published') return row.is_expired ? '已过期' : '已发布'
  if (row.status === 'draft') return '草稿'
  return '已下架'
}

function statusTag(row: any) {
  if (row.status === 'published') return row.is_expired ? 'danger' : 'success'
  if (row.status === 'draft') return 'info'
  return 'warning'
}

async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/announcements/', {
      params: {
        page: page.value,
        page_size: pageSize.value,
        status: filter.value.status || undefined,
        position: filter.value.position || undefined,
        keyword: filter.value.keyword || undefined,
      },
    })
    items.value = res.data.items || []
    total.value = res.data.total || 0
  } catch (e) {
    /* 拦截器已处理 */
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEdit.value = false
  editingId.value = null
  form.value = { title: '', content: '', content_type: 'markdown', position: 'board', start_at: '', end_at: '', sort_order: 0 }
  editVisible.value = true
}

function openEdit(row: any) {
  isEdit.value = true
  editingId.value = row.id
  form.value = {
    title: row.title,
    content: row.content,
    content_type: row.content_type,
    position: row.position,
    start_at: row.start_at,
    end_at: row.end_at,
    sort_order: row.sort_order,
  }
  editVisible.value = true
}

function validate(): boolean {
  if (!form.value.title.trim()) {
    ElMessage.warning('请输入公告标题')
    return false
  }
  if (!form.value.content.trim()) {
    ElMessage.warning('请输入公告正文')
    return false
  }
  if (!form.value.start_at || !form.value.end_at) {
    ElMessage.warning('请设置公告有效期')
    return false
  }
  if (new Date(form.value.end_at) <= new Date(form.value.start_at)) {
    ElMessage.warning('结束时间必须晚于开始时间')
    return false
  }
  return true
}

async function save() {
  if (!validate()) return
  saving.value = true
  try {
    const body = {
      title: form.value.title.trim(),
      content: form.value.content,
      content_type: form.value.content_type,
      position: form.value.position,
      start_at: form.value.start_at,
      end_at: form.value.end_at,
      sort_order: form.value.sort_order,
    }
    if (isEdit.value) {
      await request.post(`/announcements/${editingId.value}/update`, body)
      ElMessage.success('已保存')
    } else {
      await request.post('/announcements/', body)
      ElMessage.success('已创建，可在草稿中发布')
    }
    editVisible.value = false
    fetchList()
  } catch (e) {
    /* 拦截器已处理 */
  } finally {
    saving.value = false
  }
}

async function publish(row: any) {
  try {
    await request.post(`/announcements/${row.id}/publish`)
    ElMessage.success('已发布')
    fetchList()
  } catch (e) {
    /* 拦截器已处理 */
  }
}

async function unpublish(row: any) {
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
    await request.post(`/announcements/${row.id}/unpublish`)
    ElMessage.success('已下架')
    fetchList()
  } catch (e) {
    /* 拦截器已处理 */
  }
}

async function remove(row: any) {
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
    await request.post(`/announcements/${row.id}/delete`)
    ElMessage.success('已删除')
    fetchList()
  } catch (e) {
    /* 拦截器已处理 */
  }
}

async function viewDetail(row: any) {
  try {
    const res = await request.get(`/announcements/${row.id}`)
    detail.value = res.data
    detailVisible.value = true
  } catch (e) {
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
