import { computed, type Ref, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatMonthDayTime } from '@/utils/format'
import {
  createConversation,
  deleteConversation,
  listConversations,
  pinConversation,
  type ConversationItem,
} from '@/api/assistant'

/**
 * AI 会话列表管理：列表加载、置顶/最近分组、新建、置顶、删除、切换。
 * 与「聊天核心」（useChatSse）通过 conversationId 弱耦合：
 * 会话切换/删除后调用注入的 loadConversation 回流消息域，列表状态只归属本模块。
 */
export function useConversations(
  conversationId: Ref<number | null>,
  loadConversation: (id: number | null) => Promise<void>,
) {
  const aiConversations = ref<ConversationItem[]>([])
  const aiConvHoverId = ref<number | null>(null)

  // 会话分组：置顶优先，其余为最近
  const pinnedConvs = computed(() => aiConversations.value.filter(c => c.is_pinned))
  const recentConvs = computed(() => aiConversations.value.filter(c => !c.is_pinned))

  /** 刷新当前用户的会话列表 */
  async function refreshConversations() {
    try {
      const res = await listConversations()
      aiConversations.value = res?.data ?? []
    } catch {
      aiConversations.value = []
    }
  }

  /** 会话列表标题：优先 AI 自动归纳的主题名，否则会话序号 */
  function convTitle(item: ConversationItem): string {
    return item.title || `会话 #${item.id}`
  }

  /** 会话列表时间（MM-DD HH:mm） */
  function convTime(item: ConversationItem): string {
    return formatMonthDayTime(item.updated_at)
  }

  /** 新建会话（成功后置顶插入并切换） */
  async function createNewConversation() {
    try {
      const res = await createConversation()
      const conv = res?.data
      if (conv?.id) {
        aiConversations.value = [conv, ...aiConversations.value.filter(c => c.id !== conv.id)]
        await loadConversation(conv.id)
      }
    } catch {
      ElMessage.error('新建会话失败')
    }
  }

  /** 置顶 / 取消置顶会话（成功后刷新列表，后端按置顶优先排序） */
  async function togglePin(item: ConversationItem) {
    try {
      await pinConversation(item.id, !item.is_pinned)
      await refreshConversations()
    } catch {
      ElMessage.error('操作失败，请稍后再试')
    }
  }

  /** 删除会话（确认后级联清理其消息与反馈） */
  async function deleteConversationItem(id: number) {
    try {
      await ElMessageBox.confirm('删除后该会话及其消息记录将无法恢复，确定删除？', '删除会话', {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      })
    } catch {
      return // 用户取消
    }
    try {
      await deleteConversation(id)
      aiConversations.value = aiConversations.value.filter(c => c.id !== id)
      if (conversationId.value === id) {
        if (aiConversations.value.length > 0) {
          await loadConversation(aiConversations.value[0].id)
        } else {
          conversationId.value = null
          localStorage.removeItem('ai_conversation_id')
          await loadConversation(null)
        }
      }
    } catch {
      ElMessage.error('删除会话失败')
    }
  }

  return {
    aiConversations,
    aiConvHoverId,
    pinnedConvs,
    recentConvs,
    refreshConversations,
    convTitle,
    convTime,
    createNewConversation,
    togglePin,
    deleteConversationItem,
  }
}
