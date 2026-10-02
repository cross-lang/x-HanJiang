<template>
  <div>
    <el-card class="hj-mb-16">
      <div class="hj-toolbar">
        <el-button type="primary" @click="openPublish">发布通知</el-button>
        <div class="hj-flex hj-gap-8">
          <el-select
            v-model="noticeFilter.notice_type"
            placeholder="类型"
            clearable
            style="width: 130px"
            @change="fetchNotices"
          >
            <el-option label="普通通知" value="notice" />
            <el-option label="系统维护" value="maintenance" />
          </el-select>
          <el-select
            v-model="noticeFilter.status"
            placeholder="状态"
            clearable
            style="width: 130px"
            @change="fetchNotices"
          >
            <el-option label="已发布" value="published" />
            <el-option label="已撤回" value="withdrawn" />
          </el-select>
          <el-input
            v-model="noticeFilter.keyword"
            placeholder="搜索标题/正文"
            clearable
            style="width: 200px"
            @keyup.enter="fetchNotices"
            @clear="fetchNotices"
          />
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
            <el-button size="small" @click="viewNotice(row as SystemNotificationItem)">详情</el-button>
            <el-button
              v-if="row.status === 'published'"
              size="small"
              type="danger"
              link
              @click="withdraw(row as SystemNotificationItem)"
              >撤回</el-button
            >
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        class="hj-pagination hj-mt-12"
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
            <el-switch v-model="row.enabled" @change="saveConfig(row as NotificationConfig)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" @click="editConfig(row as NotificationConfig)">编辑</el-button>
            <el-button size="small" type="primary" link @click="testConfig(row as NotificationConfig)">测试</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <PublishNoticeDialog v-model:visible="publishVisible" @submitted="onPublished" />

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
          <el-descriptions-item v-if="detail.withdrawn_at" label="撤回时间">{{
            fmtTime(detail.withdrawn_at)
          }}</el-descriptions-item>
          <el-descriptions-item label="正文">{{ detail.content }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-dialog>

    <ChannelConfigDialog v-model:visible="configDialogVisible" :record="configRecord" @saved="onConfigSaved" />
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDateTime } from '@/utils/format'
import {
  listPublishedNotifications,
  getPublishedNotification,
  withdrawNotification,
  listNotificationConfigs,
  updateNotificationConfig,
  testNotificationConfig,
} from '@/api/notification'
import type { SystemNotificationItem, NotificationConfig, NoticeType } from '@/types/notification'
import PublishNoticeDialog from './components/PublishNoticeDialog.vue'
import ChannelConfigDialog from './components/ChannelConfigDialog.vue'

const notices = ref<SystemNotificationItem[]>([])
const noticeLoading = ref(false)
const noticePage = ref(1)
const noticePageSize = ref(20)
const noticeTotal = ref(0)
const noticeFilter = ref<{
  notice_type: '' | NoticeType
  status: '' | SystemNotificationItem['status']
  keyword: string
}>({
  notice_type: '',
  status: '',
  keyword: '',
})

const publishVisible = ref(false)

const detailVisible = ref(false)
const detail = ref<SystemNotificationItem | null>(null)

const configs = ref<NotificationConfig[]>([])
const configDialogVisible = ref(false)
const configRecord = ref<NotificationConfig | null>(null)

const channelNames: Record<string, string> = {
  dingtalk: '钉钉群机器人',
  feishu: '飞书群机器人',
  email: 'SMTP邮件',
}

function fmtTime(v: string | null | undefined): string {
  return formatDateTime(v)
}

async function fetchNotices() {
  noticeLoading.value = true
  try {
    const res = await listPublishedNotifications({
      page: noticePage.value,
      page_size: noticePageSize.value,
      notice_type: noticeFilter.value.notice_type || undefined,
      status: noticeFilter.value.status || undefined,
      keyword: noticeFilter.value.keyword.trim() || undefined,
    })
    notices.value = res.data.items
    noticeTotal.value = res.data.total
  } catch {
    /* 错误已由拦截器处理 */
  } finally {
    noticeLoading.value = false
  }
}

function openPublish() {
  publishVisible.value = true
}

/** 发布成功：重置分页并刷新列表 */
function onPublished() {
  publishVisible.value = false
  noticePage.value = 1
  fetchNotices()
}

async function viewNotice(row: SystemNotificationItem) {
  try {
    const res = await getPublishedNotification(row.id)
    detail.value = res.data
    detailVisible.value = true
  } catch {
    /* ignore */
  }
}

async function withdraw(row: SystemNotificationItem) {
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
    await withdrawNotification(row.id)
    ElMessage.success('已撤回')
    fetchNotices()
  } catch {
    /* ignore */
  }
}

onMounted(async () => {
  fetchNotices()
  try {
    const res = await listNotificationConfigs()
    configs.value = res.data.items
  } catch {
    /* ignore */
  }
})

function editConfig(row: NotificationConfig) {
  configRecord.value = row
  configDialogVisible.value = true
}

/** 渠道启用开关（表格内直接保存） */
async function saveConfig(row: Partial<NotificationConfig>) {
  if (!row.channel) return
  try {
    await updateNotificationConfig(row.channel, row)
    ElMessage.success('已保存')
    fetchConfigs()
  } catch {
    /* ignore */
  }
}

/** 渠道配置弹窗保存成功：关闭并刷新 */
function onConfigSaved() {
  configDialogVisible.value = false
  fetchConfigs()
}

async function testConfig(row: NotificationConfig) {
  try {
    const res = await testNotificationConfig(row.channel, row)
    if (res.data.success) {
      ElMessage.success('测试消息已发送')
    } else {
      ElMessage.error('发送失败：' + (res.data.error || '未知错误'))
    }
  } catch (e) {
    ElMessage.error('测试失败：' + ((e as Error)?.message || '网络错误'))
  }
}

async function fetchConfigs() {
  try {
    const res = await listNotificationConfigs()
    configs.value = res.data.items
  } catch {
    /* ignore */
  }
}
</script>
