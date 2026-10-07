import { nextTick, ref, watch } from 'vue'
import { chatSSE, getConversationMessages, submitFeedback, type MessageItem } from '@/api/assistant'

/** 聊天消息（含流式加载与反馈状态） */
export interface AiMsg {
  role: 'user' | 'assistant'
  content: string
  loading?: boolean
  messageId?: number | null
  feedback?: 'up' | 'down' | null
  /** 思维链内容（模型推理过程，流式透出，不落库） */
  reasoning?: string
  /** 当前执行步骤提示（如"正在调用工具：navigate"） */
  stepText?: string
  /** 思维链是否已折叠（回答开始后自动折叠，用户可展开回看） */
  reasoningCollapsed?: boolean
}

export interface UseChatSseOptions {
  /** SSE 跳转指令回调（由调用方执行路由跳转并关闭抽屉） */
  onNavigate: (path: string) => void
  /** 一轮对话完成回调（用于刷新会话列表，conversationId 可能由后端新建） */
  onConversationsChange: () => void
}

/**
 * AI 聊天核心：输入、SSE 流式对话、历史消息加载、自动滚底、👍👎 反馈。
 * 与「会话列表管理」（useConversations）通过 aiConversationId 弱耦合：
 * 本模块持有当前会话 ID 与消息域，会话列表操作通过 loadConversation 回流到消息域。
 */
export function useChatSse(options: UseChatSseOptions) {
  const aiInput = ref('')
  const aiLoading = ref(false)
  /** 最近会话ID（续聊上下文；null 表示新会话，首轮由后端自动创建） */
  const aiConversationId = ref<number | null>(Number(localStorage.getItem('ai_conversation_id')) || null)
  const aiMessages = ref<AiMsg[]>([])

  // 聊天滚动：消息变化时自动滚到底部（用户主动上翻查看历史时暂停跟随）
  const chatScrollRef = ref<HTMLElement | null>(null)

  /** 当前视口是否处于消息列表底部附近（±80px 容差） */
  function isNearBottom(): boolean {
    const el = chatScrollRef.value
    if (!el) return true
    return el.scrollHeight - el.scrollTop - el.clientHeight < 80
  }

  /** 将消息列表滚动到底部（用户新消息、助手流式输出持续跟随） */
  function scrollToBottom(): void {
    const el = chatScrollRef.value
    if (el) el.scrollTop = el.scrollHeight
  }

  watch(
    aiMessages,
    async () => {
      if (isNearBottom()) {
        await nextTick()
        scrollToBottom()
      }
    },
    { deep: true },
  )

  /** 加载指定会话的历史消息并设为当前会话 */
  async function loadConversation(id: number | null) {
    if (id === null) {
      aiMessages.value = []
      return
    }
    try {
      const res = await getConversationMessages(id)
      const items: MessageItem[] = res?.data ?? []
      aiMessages.value = items.map(item => ({
        role: item.role === 'user' ? 'user' : 'assistant',
        content: item.content,
        messageId: item.id,
        feedback: null,
      }))
      aiConversationId.value = id
      localStorage.setItem('ai_conversation_id', String(id))
    } catch {
      // 加载历史失败（如会话已失效）：重置会话，从欢迎引导开始
      aiConversationId.value = null
      localStorage.removeItem('ai_conversation_id')
      aiMessages.value = []
    }
  }

  /** 点击欢迎卡示例问题：直接作为用户输入发起对话 */
  function askQuickQuestion(question: string) {
    if (aiLoading.value) return
    aiInput.value = question
    void sendAiMessage()
  }

  async function sendAiMessage() {
    const text = aiInput.value.trim()
    if (!text || aiLoading.value) return
    aiInput.value = ''
    aiMessages.value.push({ role: 'user', content: text })
    // 助手占位消息：SSE 期间流式填充
    aiMessages.value.push({
      role: 'assistant',
      content: '',
      loading: true,
      messageId: null,
      feedback: null,
    })
    // 必须通过数组代理取回该对象再修改：若持有推入前的原始引用直接改其属性，
    // 会绕过响应式 trigger，导致流式的思考过程/正文不实时渲染，全部堆积到
    // 本轮结束其他 ref 触发重渲染时才一并出现。
    const assistantMsg = aiMessages.value[aiMessages.value.length - 1]
    aiLoading.value = true
    try {
      await chatSSE(aiConversationId.value, text, {
        onThinking: () => {
          // 可在此透出"正在思考"；默认由 loading 占位展示
        },
        onReasoning: chunk => {
          // 思维链增量：追加到 reasoning 字段，供思考过程区域流式渲染
          assistantMsg.reasoning = (assistantMsg.reasoning || '') + chunk
          assistantMsg.reasoningCollapsed = false
        },
        onStep: step => {
          // 步骤提示：替换当前步骤文本（如"正在调用 navigate 工具"）
          assistantMsg.stepText = step
        },
        onToken: chunk => {
          // 首个正式答案 token 到达：折叠思考过程，清空步骤提示
          if (assistantMsg.reasoning && !assistantMsg.reasoningCollapsed) {
            assistantMsg.reasoningCollapsed = true
          }
          assistantMsg.stepText = undefined
          assistantMsg.content += chunk
        },
        onNavigate: path => {
          // 跳转指令：执行路由跳转并关闭抽屉（剩余流式文本不再展示）
          options.onNavigate(path)
        },
        onDenied: () => {
          // 越权拒绝：模型随后会流式说明，无需额外动作
        },
        onError: message => {
          assistantMsg.content = message || '服务异常，请稍后再试'
        },
        onDone: ({ conversationId, messageId }) => {
          if (conversationId !== null && conversationId !== aiConversationId.value) {
            aiConversationId.value = conversationId
            localStorage.setItem('ai_conversation_id', String(conversationId))
          }
          assistantMsg.loading = false
          assistantMsg.messageId = messageId // 供 👍👎 反馈定位
          options.onConversationsChange()
        },
      })
    } catch (err) {
      assistantMsg.loading = false
      assistantMsg.content = (err as Error)?.message || '网络异常，请稍后再试'
    } finally {
      aiLoading.value = false
    }
  }

  /** 提交 👍👎 反馈（成功后锁定，防止重复提交） */
  async function submitAiFeedback(msg: AiMsg, positive: boolean) {
    if (msg.feedback !== null || aiConversationId.value === null || msg.messageId == null) return
    try {
      await submitFeedback({
        conversation_id: aiConversationId.value,
        message_id: msg.messageId,
        positive,
      })
      msg.feedback = positive ? 'up' : 'down'
    } catch {
      // 失败提示由请求拦截器统一处理
    }
  }

  return {
    aiInput,
    aiLoading,
    aiConversationId,
    aiMessages,
    chatScrollRef,
    loadConversation,
    askQuickQuestion,
    sendAiMessage,
    submitAiFeedback,
  }
}
