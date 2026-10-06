<template>
  <el-popover placement="bottom" :width="360" trigger="click" @show="fetchList">
    <template #reference>
      <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99" class="bell-badge">
        <el-icon :size="20" class="bell-icon"><Bell /></el-icon>
      </el-badge>
    </template>
    <div class="bell-list">
      <div v-if="list.length === 0" class="bell-empty">暂无消息</div>
      <div v-for="item in list" :key="item.id" class="bell-item" @click="openMessage(item)">
        <div class="bell-item-head">
          <div class="hj-flex-center hj-gap-8">
            <span v-if="!item.is_read" class="bell-dot"></span>
            <span class="bell-title">{{ item.title }}</span>
          </div>
          <div class="bell-time">{{ formatDateTime(item.created_at) }}</div>
        </div>
      </div>
    </div>
    <div class="bell-footer">
      <el-button text size="small" @click="markAllRead">全部已读</el-button>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Bell } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { formatDateTime } from '@/utils/format'
import { getToken } from '@/utils/storage'
import {
  getRecentStationMessages,
  markAllStationMessagesRead,
  markStationMessageRead,
  type StationMessage,
} from '@/api/notification'

const router = useRouter()
const unreadCount = ref(0)
const list = ref<StationMessage[]>([])

async function fetchList() {
  // 未登录不轮询，避免登录页持续 401
  if (!getToken()) {
    unreadCount.value = 0
    return
  }
  const res = await getRecentStationMessages(10)
  list.value = res.data.items
  unreadCount.value = res.data.unread_count
}

/** 点击消息：标记已读后按来源跳转（审批消息跳审批页，其余跳站内信列表） */
async function openMessage(item: StationMessage) {
  if (!item.is_read) {
    await markStationMessageRead(item.id)
    fetchList()
  }
  if (item.event_type === 'openapi_app_registration') {
    router.push('/app-approvals')
    return
  }
  router.push('/station-messages')
}

async function markAllRead() {
  await markAllStationMessagesRead()
  ElMessage.success('全部已读')
  fetchList()
}

let pollTimer: number | undefined

onMounted(() => {
  fetchList()
  pollTimer = window.setInterval(fetchList, 15000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.bell-badge {
  margin-right: 20px;
  cursor: pointer;
}
.bell-icon {
  color: #666;
  cursor: pointer;
}
.bell-list {
  max-height: 400px;
  overflow-y: auto;
}
.bell-empty {
  text-align: center;
  color: #999;
  padding: 30px 0;
}
.bell-item {
  border-bottom: 1px solid #f0f0f0;
}
.bell-item-head {
  padding: 12px;
  cursor: pointer;
}
.bell-dot {
  width: 8px;
  height: 8px;
  background: #f56c6c;
  border-radius: 50%;
  flex-shrink: 0;
}
.bell-title {
  font-weight: 500;
  color: #333;
}
.bell-time {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
  margin-left: 16px;
}
.bell-footer {
  padding: 8px;
  text-align: center;
  border-top: 1px solid #f0f0f0;
}
</style>
