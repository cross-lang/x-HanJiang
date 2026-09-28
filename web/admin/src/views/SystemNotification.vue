<template>
  <div>
    <el-card style="margin-bottom: 16px">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px">
        <el-button type="primary" @click="openPublish">发布通知</el-button>
        <div style="display: flex; gap: 8px">
          <el-select v-model="noticeFilter.notice_type" placeholder="类型" clearable style="width: 130px" @change="fetchNotices">
            <el-option label="普通通知" value="notice" />
            <el-option label="系统维护" value="maintenance" />
          </el-select>
          <el-select v-model="noticeFilter.status" placeholder="状态" clearable style="width: 130px" @change="fetchNotices">
            <el-option label="已发布" value="published" />
            <el-option label="已撤回" value="withdrawn" />
          </el-select>
          <el-input v-model="noticeFilter.keyword" placeholder="搜索标题/正文" clearable style="width: 200px" @keyup.enter="fetchNotices" @clear="fetchNotices" />
          <el-button type="primary" icon="Search" @click="fetchNotices">搜索</el-button>
        </div>
      </div>
      <el-table :data="notices" v-loading="noticeLoading" border>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column label="类型" width="110">
          <template #default="{ row }">
            <el-tag :type="row.notice_type === 'maintenance' ? 'warning' : 'info'">
              {{ row.notice_type === 'maintenance' ? '系统维护' : '普通通知' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'withdrawn' ? 'danger' : 'success'">
              {{ row.status === 'withdrawn' ? '已撤回' : '已发布' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="operator_name" label="发布人" width="120" />
        <el-table-column label="发布时间" width="170">
          <template #default="{ row }">{{ fmtTime(row.published_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" @click="viewNotice(row)">详情</el-button>
            <el-button
              v-if="row.status === 'published'"
              size="small"
              type="danger"
              link
              @click="withdraw(row)"
            >撤回</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        style="margin-top: 12px; justify-content: flex-end; display: flex"
        v-model:current-page="noticePage"
        v-model:page-size="noticePageSize"
        :total="noticeTotal"
        layout="total, prev, pager, next"
        @current-change="fetchNotices"
      />
    </el-card>

    <el-card>
      <template #header>
        <span>通知渠道配置</span>
      </template>
      <el-table :data="configs" border>
        <el-table-column prop="channel" label="渠道" width="160">
          <template #default="{ row }">
            <el-tag>{{ channelNames[row.channel] || row.channel }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="config_json" label="配置" show-overflow-tooltip />
        <el-table-column prop="enabled" label="启用" width="80">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" @change="saveConfig(row)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" @click="editConfig(row)">编辑</el-button>
            <el-button size="small" type="primary" link @click="testConfig(row)">测试</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="publishVisible" title="发布通知" width="560px">
      <el-form :model="publishForm" label-width="90px">
        <el-form-item label="通知类型">
          <el-radio-group v-model="publishForm.notice_type">
            <el-radio value="notice">普通通知</el-radio>
            <el-radio value="maintenance">系统维护</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="publishForm.title" maxlength="200" placeholder="通知标题" />
        </el-form-item>
        <el-form-item v-if="publishForm.notice_type !== 'maintenance'" label="正文">
          <el-input v-model="publishForm.content" type="textarea" :rows="5" maxlength="5000" placeholder="通知正文，将推送至全体用户的站内信" />
        </el-form-item>
        <template v-if="publishForm.notice_type === 'maintenance'">
          <el-form-item label="维护时间">
            <el-date-picker
              v-model="publishForm.maintenance_time"
              type="datetime"
              placeholder="选择维护开始时间"
              style="width: 100%"
              format="YYYY-MM-DD HH:mm"
              value-format="YYYY-MM-DD HH:mm:ss"
              :disabled-date="disablePastDate"
            />
          </el-form-item>
          <el-form-item label="预计时长">
            <el-input v-model="publishForm.duration" placeholder="如 2 小时（需包含单位）" />
          </el-form-item>
          <el-form-item label="维护原因">
            <el-input v-model="publishForm.reason" placeholder="可选" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="publishVisible = false">取消</el-button>
        <el-button type="primary" :loading="publishing" @click="doPublish">发布</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="通知详情" width="620px">
      <template v-if="detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="标题">{{ detail.title }}</el-descriptions-item>
          <el-descriptions-item label="类型">
            <el-tag :type="detail.notice_type === 'maintenance' ? 'warning' : 'info'">
              {{ detail.notice_type === 'maintenance' ? '系统维护' : '普通通知' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="detail.status === 'withdrawn' ? 'danger' : 'success'">
              {{ detail.status === 'withdrawn' ? '已撤回' : '已发布' }}
            </el-tag>
          </el-descriptions-item>
          <template v-if="detail.notice_type === 'maintenance'">
            <el-descriptions-item label="维护时间">{{ detail.maintenance_time || '-' }}</el-descriptions-item>
            <el-descriptions-item label="预计时长">{{ detail.duration || '-' }}</el-descriptions-item>
            <el-descriptions-item label="维护原因">{{ detail.reason || '-' }}</el-descriptions-item>
          </template>
          <el-descriptions-item label="发布人">{{ detail.operator_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="发布时间">{{ fmtTime(detail.published_at) || '-' }}</el-descriptions-item>
          <el-descriptions-item v-if="detail.withdrawn_at" label="撤回时间">{{ fmtTime(detail.withdrawn_at) }}</el-descriptions-item>
          <el-descriptions-item label="正文">{{ detail.content }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-dialog>

    <el-dialog v-model="configDialogVisible" title="编辑渠道配置" width="500px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="渠道">
          <el-input v-model="editForm.channel" disabled />
        </el-form-item>
        <el-form-item label="配置JSON">
          <el-input v-model="editForm.config_json" type="textarea" :rows="8" placeholder='{"webhook": "https://..."}' />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="editForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="configDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveConfig(editForm)">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/api/request'

const notices = ref<any[]>([])
const noticeLoading = ref(false)
const noticePage = ref(1)
const noticePageSize = ref(20)
const noticeTotal = ref(0)
const noticeFilter = ref({ notice_type: '', status: '', keyword: '' })

const publishVisible = ref(false)
const publishing = ref(false)
const publishForm = ref<any>({
  notice_type: 'notice',
  title: '',
  content: '',
  maintenance_time: '',
  duration: '',
  reason: '',
})

const detailVisible = ref(false)
const detail = ref<any>(null)

const configs = ref<any[]>([])
const configDialogVisible = ref(false)
const editForm = ref<any>({})

const channelNames: Record<string, string> = {
  dingtalk: '钉钉群机器人',
  feishu: '飞书群机器人',
  email: 'SMTP邮件',
}

function fmtTime(v: string | null | undefined): string {
  if (!v) return ''
  return v.replace('T', ' ').slice(0, 19)
}

function disablePastDate(date: Date): boolean {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return date.getTime() < today.getTime()
}

async function fetchNotices() {
  noticeLoading.value = true
  try {
    const params: any = { page: noticePage.value, page_size: noticePageSize.value }
    if (noticeFilter.value.notice_type) params.notice_type = noticeFilter.value.notice_type
    if (noticeFilter.value.status) params.status = noticeFilter.value.status
    if (noticeFilter.value.keyword.trim()) params.keyword = noticeFilter.value.keyword.trim()
    const res = await request.get('/notifications/published', { params })
    notices.value = res.data.items || []
    noticeTotal.value = res.data.total || 0
  } catch (e) {
    /* 错误已由拦截器处理 */
  } finally {
    noticeLoading.value = false
  }
}

function openPublish() {
  publishForm.value = { notice_type: 'notice', title: '', content: '', maintenance_time: '', duration: '', reason: '' }
  publishVisible.value = true
}

async function doPublish() {
  const form = publishForm.value
  if (!form.title.trim()) {
    ElMessage.warning('请输入通知标题')
    return
  }
  if (form.notice_type === 'maintenance' && (!form.maintenance_time.trim() || !form.duration.trim())) {
    ElMessage.warning('系统维护通知必须填写维护时间与预计时长')
    return
  }
  if (form.notice_type === 'maintenance' && !/(小时|时|h|分钟|分|天)/.test(form.duration.trim())) {
    ElMessage.warning('预计持续时长需包含单位，如 2 小时')
    return
  }
  if (form.notice_type === 'maintenance') {
    const mt = new Date(form.maintenance_time.replace(/-/g, '/'))
    if (isNaN(mt.getTime()) || mt.getTime() <= Date.now()) {
      ElMessage.warning('维护时间不能早于当前时间')
      return
    }
  }
  if (form.notice_type !== 'maintenance' && !form.content.trim()) {
    ElMessage.warning('请输入通知正文')
    return
  }
  publishing.value = true
  try {
    const body: any = { title: form.title.trim(), notice_type: form.notice_type }
    if (form.notice_type === 'maintenance') {
      body.maintenance_time = form.maintenance_time.trim()
      body.duration = form.duration.trim()
      body.reason = form.reason.trim() || undefined
    } else {
      body.content = form.content.trim()
    }
    const res = await request.post('/notifications/publish', body)
    const sent = res.data.sent_count
    ElMessage.success(sent != null ? `已发布，站内信推送完成（多渠道推送 ${sent} 人）` : '已发布')
    publishVisible.value = false
    noticePage.value = 1
    fetchNotices()
  } catch (e) {
    /* 错误已由拦截器处理 */
  } finally {
    publishing.value = false
  }
}

async function viewNotice(row: any) {
  try {
    const res = await request.get(`/notifications/published/${row.id}`)
    detail.value = res.data
    detailVisible.value = true
  } catch (e) {
    /* ignore */
  }
}

async function withdraw(row: any) {
  try {
    await ElMessageBox.confirm(`确认撤回通知「${row.title}」？撤回后用户将不再看到该通知。`, '撤回确认', {
      type: 'warning',
      confirmButtonText: '撤回',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await request.post(`/notifications/${row.id}/withdraw`)
    ElMessage.success('已撤回')
    fetchNotices()
  } catch (e) {
    /* ignore */
  }
}

onMounted(async () => {
  fetchNotices()
  try {
    const res = await request.get('/admin/notification-configs')
    configs.value = res.data.items
  } catch (e) {
    /* ignore */
  }
})

function editConfig(row: any) {
  editForm.value = { ...row }
  configDialogVisible.value = true
}

async function saveConfig(row: any) {
  try {
    await request.put(`/admin/notification-configs/${row.channel}`, row)
    ElMessage.success('已保存')
    configDialogVisible.value = false
  } catch (e) {
    /* ignore */
  }
}

async function testConfig(row: any) {
  try {
    const res = await request.post(`/admin/notification-configs/${row.channel}/test`)
    if (res.data.success) {
      ElMessage.success('测试消息已发送')
    } else {
      ElMessage.error('发送失败：' + (res.data.error || '未知错误'))
    }
  } catch (e: any) {
    ElMessage.error('测试失败：' + (e?.message || '网络错误'))
  }
}
</script>
