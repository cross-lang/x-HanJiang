/** AI 助手类型（与 server/src/schemas/assistant.py 对齐） */

export interface ConversationItem {
  id: number
  user_id: number
  title: string | null
  summary: string | null
  is_pinned: boolean
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
