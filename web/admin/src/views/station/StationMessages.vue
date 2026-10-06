<template>
  <div>
    <el-card>
      <div class="hj-toolbar">
        <div class="hj-flex hj-gap-8">
          <el-select v-model="filter.source" placeholder="来源" clearable style="width: 150px" @change="fetchList">
            <el-option v-for="(label, value) in SOURCE_LABELS" :key="value" :label="label" :value="value" />
          </el-select>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="~"
            start-placeholder="接收起始日期"
            end-placeholder="接收截止日期"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 300px"
            @change="fetchList"
          />
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
        <el-button type="primary" :icon="Download" @click="handleExport">导出 CSV</el-button>
      </div>

      <el-table :data="items" v-loading="loading" border>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="content" label="内容" min-width="260" show-overflow-tooltip />
        <el-table-column label="来源" width="120">
          <template #default="{ row }">
            <el-tag :type="sourceTag(row.source as string)" effect="plain">
              {{ SOURCE_LABELS[row.source as string] || row.source || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="事件类型" width="180" show-overflow-tooltip>
          <template #default="{ row }">
            {{ EVENT_LABELS[row.event_type as string] || row.event_type || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_read ? 'info' : 'success'">{{ row.is_read ? '已读' : '未读' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="接收时间" width="170" />
        <el-table-column label="操作" width="110">
          <template #default="{ row }">
            <el-button size="small" @click="viewDetail(row as StationMessage)">详情</el-button>
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

    <el-dialog v-model="detailVisible" title="站内信详情" width="680px">
      <template v-if="detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="标题">{{ detail.title }}</el-descriptions-item>
          <el-descriptions-item label="来源">
            <el-tag :type="sourceTag(detail.source as string)" effect="plain">
              {{ SOURCE_LABELS[detail.source as string] || detail.source || '-' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="事件类型">
            {{ EVENT_LABELS[detail.event_type as string] || detail.event_type || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="detail.is_read ? 'info' : 'success'">{{ detail.is_read ? '已读' : '未读' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="接收时间">{{ detail.created_at }}</el-descriptions-item>
          <el-descriptions-item v-if="detail.read_at" label="已读时间">{{ detail.read_at }}</el-descriptions-item>
          <el-descriptions-item label="正文">
            <div class="station-content">{{ detail.content }}</div>
          </el-descriptions-item>
        </el-descriptions>
      </template>
    </el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import { listStationMessages, getStationMessage, exportStationMessagesCsv } from '@/api/notification'
import type { StationMessage } from '@/api/notification'
import { downloadResponseBlob } from '@/utils/download'

/** 来源 → 中文名映射（与后端 NotificationSource 枚举对齐） */
const SOURCE_LABELS: Record<string, string> = {
  system_notice: '系统通知',
  station: '站内信',
  alert: '系统告警',
  openapi_app: '开放平台',
}

/** 已知事件类型 → 中文名映射（未知类型展示原始标识） */
const EVENT_LABELS: Record<string, string> = {
  'system.notice': '系统通知',
  'system.alert': '系统告警',
  'station.message': '站内消息',
  'openapi_app.created': '开放应用创建',
  'openapi_app.updated': '开放应用更新',
  'openapi_app.deleted': '开放应用删除',
  'openapi_app.key_reset': '开放应用密钥重置',
  'user.created': '新用户创建',
  'user.deleted': '用户已删除',
  'user.password_changed': '密码修改',
  'user.profile_updated': '资料变更',
  'user.status_changed': '账号状态变更',
  'role.assigned': '角色变更',
  'role.deleted': '角色已删除',
  'permission.granted': '权限授予',
  'permission.revoked': '权限回收',
  'file.uploaded': '文件上传',
  'file.deleted': '文件删除',
  'file.downloaded': '文件下载',
  'login.new_device': '新设备登录',
  openapi_app_registration: '开放应用审批',
}

function sourceTag(source: string): 'primary' | 'success' | 'warning' | 'info' {
  switch (source) {
    case 'alert':
      return 'warning'
    case 'openapi_app':
      return 'primary'
    case 'station':
      return 'info'
    default:
      return 'success'
  }
}

const items = ref<StationMessage[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const filter = ref<{ source: string; keyword: string }>({ source: '', keyword: '' })
const dateRange = ref<[string, string] | null>(null)

const detailVisible = ref(false)
const detail = ref<StationMessage | null>(null)

async function fetchList() {
  loading.value = true
  try {
    const res = await listStationMessages({
      page: page.value,
      page_size: pageSize.value,
      source: filter.value.source || undefined,
      start_date: dateRange.value?.[0] || undefined,
      end_date: dateRange.value?.[1] || undefined,
      keyword: filter.value.keyword || undefined,
    })
    items.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

async function viewDetail(row: StationMessage) {
  const res = await getStationMessage(row.id)
  detail.value = res.data
  detailVisible.value = true
}

async function handleExport() {
  try {
    const resp = await exportStationMessagesCsv({
      source: filter.value.source || undefined,
      start_date: dateRange.value?.[0] || undefined,
      end_date: dateRange.value?.[1] || undefined,
      keyword: filter.value.keyword || undefined,
    })
    if (!resp.ok) {
      ElMessage.error('导出失败')
      return
    }
    await downloadResponseBlob(resp, 'station_messages_export.csv')
    ElMessage.success('导出成功')
  } catch {
    ElMessage.error('导出失败')
  }
}

onMounted(fetchList)
</script>

<style scoped>
.station-content {
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.7;
  color: var(--el-text-color-primary);
}
</style>
