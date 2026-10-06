/** 系统通知与通知配置类型（与 server/src/schemas/notification.py 对齐） */

export type NoticeType = 'notice' | 'maintenance'
export type NoticeStatus = 'published' | 'withdrawn'

export interface SystemNotificationItem {
  id: number
  title: string
  content: string
  notice_type: NoticeType
  status: NoticeStatus
  operator_id: number | null
  operator_name: string | null
  /** 扩展元数据：维护参数 / 受众快照 / 强推渠道 / 强推成功数 */
  metadata_json: {
    maintenance_time?: string
    duration_hours?: number | string
    reason?: string
    push_channels?: string[]
    target_type?: string
    target_roles?: string[]
    target_user_ids?: number[]
    sent_count?: number
    [key: string]: unknown
  } | null
  published_at: string | null
  withdrawn_at: string | null
  created_at: string | null
  updated_at: string | null
}

export interface NotificationConfig {
  channel: string
  recipient: string
  config: Record<string, unknown>
  enabled: boolean
  updated_at: string | null
}

export interface NotificationPreferenceMap {
  [event: string]: { [channel: string]: boolean }
}
