<template>
  <el-popover placement="bottom" :width="360" trigger="click" @show="fetchList">
    <template #reference>
      <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99" style="margin-right: 20px; cursor: pointer">
        <el-icon :size="20" style="color: #666; cursor: pointer"><Bell /></el-icon>
      </el-badge>
    </template>
    <div style="max-height: 400px; overflow-y: auto">
      <div v-if="list.length === 0" style="text-align: center; color: #999; padding: 30px 0">暂无消息</div>
      <div v-for="item in list" :key="item.id" style="border-bottom: 1px solid #f0f0f0">
        <div style="padding: 12px; cursor: pointer" @click="toggleExpand(item)">
          <div style="display: flex; align-items: center; gap: 8px">
            <span v-if="!item.is_read" style="width: 8px; height: 8px; background: #f56c6c; border-radius: 50%; flex-shrink: 0"></span>
            <span style="font-weight: 500; color: #333">{{ item.title }}</span>
          </div>
          <div style="font-size: 12px; color: #999; margin-top: 4px; margin-left: 16px">{{ formatDateTime(item.created_at) }}</div>
        </div>
        <div v-if="expandedId === item.id" style="padding: 8px 12px 12px 16px; background: #fafafa; font-size: 13px; color: #666">
          {{ item.content }}
        </div>
      </div>
    </div>
    <div style="padding: 8px; text-align: center; border-top: 1px solid #f0f0f0">
      <el-button text size="small" @click="markAllRead">全部已读</el-button>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { Bell } from '@element-plus/icons-vue'
import request from '@/api/request'
import { ElMessage } from 'element-plus'
import { formatDateTime } from '@/utils/format'

const unreadCount = ref(0)
const list = ref<any[]>([])
const expandedId = ref<number | null>(null)

async function fetchUnread() {
  // 未登录不轮询，避免登录页持续 401
  if (!localStorage.getItem('access_token')) {
    unreadCount.value = 0
    return
  }
  const res = await request.get('/station/messages/unread-count')
  unreadCount.value = res.data.count
}

async function fetchList() {
  const res = await request.get('/station/messages', { params: { page: 1, page_size: 10 } })
  list.value = res.data.items
}

async function toggleExpand(item: any) {
  expandedId.value = expandedId.value === item.id ? null : item.id
  if (!item.is_read) {
    await request.post(`/station/messages/${item.id}/read`)
    fetchUnread()
  }
}

async function markAllRead() {
  await request.post('/station/messages/read-all')
  ElMessage.success('全部已读')
  fetchUnread()
  fetchList()
}

let pollTimer: number | undefined

onMounted(() => {
  fetchUnread()
  pollTimer = window.setInterval(fetchUnread, 15000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>
