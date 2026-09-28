import request from './request'

// ============================================================
// AI 助手 API
// 后端：POST /assistant/chat（SSE 流式）/ POST /assistant/conversations
//      GET /assistant/conversations / GET /assistant/conversations/{id}/messages
//      POST /assistant/feedback
// 统一响应结构：{ code, message, data, timestamp, request_id }（data 为业务数据）
// ============================================================

export interface ConversationItem {
  id: number
  user_id: number
  summary: string | null
  created_at: string
  updated_at: string
}

export interface MessageItem {
  id: number
  conversation_id: number
  role: string
  content: string
  created_at: string
}

export interface ChatDoneInfo {
  conversationId: number | null
  messageId: number | null
}

export interface ChatSSEHandlers {
  onThinking?: () => void
  onToken: (text: string) => void
  onNavigate: (path: string) => void
  onDenied: () => void
  onError: (message: string) => void
  onDone: (info: ChatDoneInfo) => void
}

/** 查询当前用户会话列表 */
export function listConversations() {
  return request.get('/assistant/conversations')
}

/** 查询指定会话消息（时间正序） */
export function getConversationMessages(conversationId: number) {
  return request.get(`/assistant/conversations/${conversationId}/messages`)
}

/** 创建新会话 */
export function createConversation() {
  return request.post('/assistant/conversations')
}

/** 消息反馈（👍👎） */
export function submitFeedback(data: {
  conversation_id: number
  message_id: number
  positive: boolean
  comment?: string
}) {
  return request.post('/assistant/feedback', data)
}

/**
 * SSE 流式对话（POST 流式，axios 无法流式消费，使用 fetch + ReadableStream）。
 * 事件协议（与后端 AssistantEventType 对齐）：
 *   thinking → token → navigate/denied → error → done
 * @param conversationId 会话ID（null 时后端自动创建，done 事件回传）
 * @param message 用户输入
 * @param handlers 事件回调
 */
export async function chatSSE(
  conversationId: number | null,
  message: string,
  handlers: ChatSSEHandlers,
): Promise<void> {
  const token = localStorage.getItem('access_token')
  const resp = await fetch('/api/v1/assistant/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ conversation_id: conversationId, message }),
  })
  if (!resp.ok) {
    let msg = `请求失败（${resp.status}）`
    try {
      const body = await resp.json()
      if (body?.message) msg = body.message
    } catch {
      /* 非 JSON 错误体，忽略 */
    }
    if (resp.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    throw new Error(msg)
  }
  if (!resp.body) {
    throw new Error('当前浏览器不支持流式响应')
  }
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let sep: number
    while ((sep = buffer.indexOf('\n\n')) >= 0) {
      const frame = buffer.slice(0, sep)
      buffer = buffer.slice(sep + 2)
      if (!frame.startsWith('data:')) continue
      const payload = frame.replace(/^data:\s*/, '').trim()
      if (!payload) continue
      let event: Record<string, unknown>
      try {
        event = JSON.parse(payload)
      } catch {
        continue
      }
      switch (event.type) {
        case 'thinking':
          handlers.onThinking?.()
          break
        case 'token':
          handlers.onToken(String(event.content ?? ''))
          break
        case 'navigate':
          handlers.onNavigate(String(event.path ?? ''))
          break
        case 'denied':
          handlers.onDenied()
          break
        case 'error':
          handlers.onError(String(event.message ?? '服务异常，请稍后再试'))
          break
        case 'done':
          handlers.onDone({
            conversationId:
              typeof event.conversation_id === 'number' ? event.conversation_id : null,
            messageId: typeof event.message_id === 'number' ? event.message_id : null,
          })
          break
        default:
          break
      }
    }
  }
}
