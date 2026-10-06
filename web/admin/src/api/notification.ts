import request from './request'
import type { PageResult } from '@/types/api'
import type { SystemNotificationItem, NotificationConfig, NoticeType, NoticeStatus } from '@/types/notification'

export interface NotificationQuery {
  page: number
  page_size: number
  keyword?: string
  status?: NoticeStatus
  notice_type?: NoticeType
}

export function listPublishedNotifications(params: NotificationQuery) {
  return request.get<PageResult<SystemNotificationItem>>('/notifications/published', { params })
}

export function getPublishedNotification(id: number) {
  return request.get<SystemNotificationItem>(`/notifications/published/${id}`)
}

export function publishNotification(data: {
  title: string
  content: string
  notice_type: NoticeType
  maintenance_time?: string | null
  /** 预计持续时长（小时数，整数或小数） */
  duration_hours?: number | null
  reason?: string | null
  /** 强推渠道列表（站内信已默认广播，可选 email/dingtalk/feishu） */
  push_channels?: string[]
  /** 发布幂等键：同一请求重复提交返回首次结果 */
  client_request_id?: string
  /** 发布受众类型（all 全员 / roles 指定角色 / users 指定用户） */
  target_type?: 'all' | 'roles' | 'users'
  /** 目标角色编码列表（target_type=roles 时必填） */
  target_roles?: string[]
  /** 目标用户 ID 列表（target_type=users 时必填） */
  target_user_ids?: number[]
}) {
  return request.post<SystemNotificationItem & { sent_count?: number; idempotent?: boolean }>(
    '/notifications/publish',
    data,
  )
}

export function withdrawNotification(id: number) {
  return request.post<{ message: string }>(`/notifications/${id}/withdraw`)
}

/** 重新发布已撤回的系统通知（按首次发布的受众快照重新广播） */
export function republishNotification(id: number) {
  return request.post<SystemNotificationItem & { sent_count?: number }>(`/notifications/${id}/republish`)
}

export interface NotificationDeliveryItem {
  id: number
  user_id?: number | null
  channel: string
  recipient: string
  status: string
  retry_count: number
  max_retries: number
  error_message?: string | null
  receive_at?: string | null
  created_at?: string | null
}

export interface NotificationDeliveryPage {
  items: NotificationDeliveryItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
  /** 按投递状态统计（pending/success/failed...） */
  stats: Record<string, number>
}

/** 系统通知投递明细（可按渠道/状态过滤） */
export function listNotificationDeliveries(
  id: number,
  params: { page: number; page_size: number; channel?: string; status?: string },
) {
  return request.get<NotificationDeliveryPage>(`/notifications/${id}/deliveries`, { params })
}

export function listNotificationConfigs() {
  return request.get<PageResult<NotificationConfig>>('/notification-configs')
}

export function updateNotificationConfig(channel: string, data: Partial<NotificationConfig>) {
  return request.put<NotificationConfig>(`/notification-configs/${channel}`, data)
}

export function testNotificationConfig(channel: string, data: Partial<NotificationConfig>) {
  return request.post<{ success: boolean; error?: string }>(`/notification-configs/${channel}/test`, data)
}

/** 站内信：未读数 */
export function getUnreadCount() {
  return request.get<{ count: number }>('/station/messages/unread-count')
}

export interface StationMessageRecent {
  items: StationMessage[]
  unread_count: number
}

/** 最近站内信（铃铛下拉：一次返回最近条数 + 未读数） */
export function getRecentStationMessages(limit = 10) {
  return request.get<StationMessageRecent>('/station/messages/recent', { params: { limit } })
}

export interface StationMessage {
  id: number
  title: string
  content: string
  /** 事件类型（如 openapi_app_registration：开放应用申请待审批） */
  event_type: string
  /** 事件类型中文名（后端由 NotificationEvent 枚举映射） */
  event_type_label?: string
  /** 消息来源（system_notice/station/alert/openapi_app，前端跳转依据） */
  source?: string
  /** 来源中文名（后端由 NotificationSource 枚举映射） */
  source_label?: string
  is_read: boolean
  created_at: string
  /** 已读时间（详情接口返回） */
  read_at?: string
}

export interface StationMessageQuery {
  page: number
  page_size: number
  /** 来源过滤 */
  source?: string
  /** 接收起始时间（含） */
  start_date?: string
  /** 接收截止时间（含） */
  end_date?: string
  /** 关键词（模糊匹配标题/正文） */
  keyword?: string
}

export function listStationMessages(params: StationMessageQuery) {
  return request.get<PageResult<StationMessage>>('/station/messages', { params })
}

export function getStationMessage(id: number) {
  return request.get<StationMessage>(`/station/messages/${id}`)
}

export function markStationMessageRead(id: number) {
  return request.post<{ message: string }>(`/station/messages/${id}/read`)
}

export function markAllStationMessagesRead() {
  return request.post<{ message: string }>('/station/messages/read-all')
}

/** 导出站内信 CSV（原始 fetch，后端直接返回文件流） */
export function exportStationMessagesCsv(params: {
  source?: string
  start_date?: string
  end_date?: string
  keyword?: string
}): Promise<Response> {
  const query = new URLSearchParams()
  if (params.source) query.set('source', params.source)
  if (params.start_date) query.set('start_date', params.start_date)
  if (params.end_date) query.set('end_date', params.end_date)
  if (params.keyword) query.set('keyword', params.keyword)
  const suffix = query.toString()
  const token = localStorage.getItem('access_token')
  return fetch(`/api/admin/v1/station/messages/export${suffix ? `?${suffix}` : ''}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
}
