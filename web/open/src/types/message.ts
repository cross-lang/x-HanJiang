/** 站内信类型（预留：开发者站内信/消息中心） */

export interface OpenMessage {
  id: number
  title: string
  content: string
  /** 消息类型：system / audit / notify */
  category: 'system' | 'audit' | 'notify'
  read: boolean
  created_at: string
}
