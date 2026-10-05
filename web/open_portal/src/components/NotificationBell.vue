<template>
  <el-popover placement="bottom" :width="360" trigger="click" @show="fetchList">
    <template #reference>
      <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99" class="bell-badge">
        <el-icon :size="20" class="bell-icon"><Bell /></el-icon>
      </el-badge>
    </template>
    <div class="bell-list">
      <div v-if="loading" class="bell-empty">加载中…</div>
      <div v-else-if="list.length === 0" class="bell-empty">暂无消息</div>
      <div v-for="item in list" :key="item.id" class="bell-item">
        <div class="bell-item-head" @click="toggleExpand(item)">
          <div class="hj-flex-center hj-gap-8">
            <span v-if="!item.read" class="bell-dot"></span>
            <span class="bell-title">{{ item.title }}</span>
            <el-tag size="small" :type="tagTypeOf(item.category)" class="bell-tag">
              {{ MESSAGE_CATEGORY_LABELS[item.category] || item.category }}
            </el-tag>
          </div>
          <div class="bell-time">{{ formatDateTime(item.created_at) }}</div>
        </div>
        <div v-if="expandedId === item.id" class="bell-content">
          {{ item.content }}
        </div>
      </div>
    </div>
    <div class="bell-footer">
      <el-button text size="small" :disabled="list.length === 0" @click="markAllRead">全部已读</el-button>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Bell } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { formatDateTime } from '@/utils/format'
import { getToken } from '@/utils/storage'
import { getUnreadCount, listMessages, markAllMessagesRead, markMessageRead } from '@/api/messages'
import { MESSAGE_CATEGORY_LABELS, type OpenMessage } from '@/types/message'

const router = useRouter()
const unreadCount = ref(0)
const list = ref<OpenMessage[]>([])
const expandedId = ref<number | null>(null)
const loading = ref(false)

function tagTypeOf(category: OpenMessage['category']): 'primary' | 'warning' | 'success' | 'info' {
  if (category === 'audit') return 'warning'
  if (category === 'notify') return 'success'
  return 'primary'
}

async function fetchUnread() {
  // 未登录不轮询，避免登录页持续 401
  if (!getToken()) {
    unreadCount.value = 0
    return
  }
  const res = await getUnreadCount()
  unreadCount.value = res.data.count
}

async function fetchList() {
  loading.value = true
  try {
    const res = await listMessages({ page: 1, page_size: 10 })
    list.value = res.data.items
  } catch {
    // 错误已处理
  } finally {
    loading.value = false
  }
}

async function toggleExpand(item: OpenMessage) {
  // 审批结果类站内信（category=audit / 标题含"审批"）：直接跳转应用管理查看最新状态，
  // 跳转优先于已读操作（已读异步执行，失败不阻塞跳转）
  if (item.category === 'audit' || item.title.includes('审批')) {
    if (!item.read) {
      markLocalRead(item.id)
      void markMessageRead(item.id).catch(() => {})
      fetchUnread()
    }
    router.push('/apps')
    return
  }
  expandedId.value = expandedId.value === item.id ? null : item.id
  if (!item.read) {
    try {
      await markMessageRead(item.id)
      // 已读成功后同步本地列表状态：条目左侧红点立即消失（无需重开面板）
      markLocalRead(item.id)
    } catch {
      // 已读失败不影响展开
    }
    fetchUnread()
  }
}

/** 将本地列表中指定消息标记为已读（同步条目红点与角标） */
function markLocalRead(id: number) {
  const target = list.value.find(m => m.id === id)
  if (target) target.read = true
}

async function markAllRead() {
  await markAllMessagesRead()
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

<style scoped>
.bell-badge {
  margin-right: 20px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  transition: background 0.15s ease;
}
.bell-badge:hover {
  background: var(--hj-bg-hover);
}
.bell-icon {
  color: var(--hj-text-body);
  cursor: pointer;
}
.bell-list {
  max-height: 400px;
  overflow-y: auto;
}
.bell-empty {
  text-align: center;
  color: var(--hj-text-secondary);
  padding: 30px 0;
}
.bell-item {
  border-bottom: 1px solid var(--hj-border-lighter);
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
  color: var(--hj-text-title);
}
.bell-tag {
  margin-left: 2px;
}
.bell-time {
  font-size: 12px;
  color: var(--hj-text-muted);
  margin-top: 4px;
  margin-left: 16px;
}
.bell-content {
  padding: 8px 12px 12px 16px;
  background: var(--hj-bg-page);
  font-size: 13px;
  color: var(--hj-text-body);
}
.bell-footer {
  padding: 8px;
  text-align: center;
  border-top: 1px solid var(--hj-border-lighter);
}
</style>
