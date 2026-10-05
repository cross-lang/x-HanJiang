import request from './request'
import type { PageResult } from '@/types/api'
import type {
  SystemNotificationItem,
  NotificationConfig,
  NotificationRecord,
  NoticeType,
  NoticeStatus,
} from '@/types/notification'

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
  duration?: string | null
  reason?: string | null
}) {
  return request.post<SystemNotificationItem & { sent_count?: number }>('/notifications/publish', data)
}

export function withdrawNotification(id: number) {
  return request.post<{ message: string }>(`/notifications/${id}/withdraw`)
}

export function listNotificationConfigs() {
  return request.get<PageResult<NotificationConfig>>('/admin/notification-configs')
}

export function updateNotificationConfig(channel: string, data: Partial<NotificationConfig>) {
  return request.put<NotificationConfig>(`/admin/notification-configs/${channel}`, data)
}

export function testNotificationConfig(channel: string, data: Partial<NotificationConfig>) {
  return request.post<{ success: boolean; error?: string }>(`/admin/notification-configs/${channel}/test`, data)
}

export function listNotificationRecords(params: NotificationQuery) {
  return request.get<PageResult<NotificationRecord>>('/admin/notification-records', { params })
}

/** 站内信：未读数 */
export function getUnreadCount() {
  return request.get<{ count: number }>('/station/messages/unread-count')
}

export interface StationMessage {
  id: number
  title: string
  content: string
  /** 事件类型（如 openapi_app_registration：开放应用申请待审批） */
  event_type: string
  is_read: boolean
  created_at: string
}

export function listStationMessages() {
  return request.get<PageResult<StationMessage>>('/station/messages', { params: { page: 1, page_size: 10 } })
}

export function markStationMessageRead(id: number) {
  return request.post<{ message: string }>(`/station/messages/${id}/read`)
}

export function markAllStationMessagesRead() {
  return request.post<{ message: string }>('/station/messages/read-all')
}
