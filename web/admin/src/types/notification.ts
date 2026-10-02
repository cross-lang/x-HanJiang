/** 系统通知与通知配置类型（与 server/src/schemas/notification.py 对齐） */

export type NoticeType = 'notice' | 'maintenance'
export type NoticeStatus = 'published' | 'withdrawn'

export interface SystemNotificationItem {
  id: number
  title: string
  content: string
  notice_type: NoticeType
  maintenance_time: string | null
  duration: string | null
  reason: string | null
  status: NoticeStatus
  operator_id: number | null
  operator_name: string | null
  published_at: string | null
  withdrawn_at: string | null
  created_at: string | null
}

export interface NotificationConfig {
  channel: string
  recipient: string
  config_json: string
  enabled: boolean
  updated_at: string | null
}

export interface NotificationRecord {
  id: number
  event_type: string
  channel: string
  recipient: string
  subject: string
  content: string
  status: string
  retry_count: number
  error_message: string | null
  created_at: string
  sent_at: string | null
}

export interface NotificationStats {
  total: number
  success: number
  failed: number
  pending: number
}

export interface NotificationPreferenceMap {
  [event: string]: { [channel: string]: boolean }
}
