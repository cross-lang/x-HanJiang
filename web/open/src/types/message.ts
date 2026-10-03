/** 开放平台门户：开发者站内信类型（后端 developer_messages 表） */

export interface OpenMessage {
  id: number
  title: string
  content: string
  /** 消息类型：system 系统消息 / audit 审批结果 / notify 业务通知 */
  category: 'system' | 'audit' | 'notify'
  /** 是否已读 */
  read: boolean
  created_at: string
}

/** 消息类型中文标签 */
export const MESSAGE_CATEGORY_LABELS: Record<OpenMessage['category'], string> = {
  system: '系统',
  audit: '审批',
  notify: '通知',
}
