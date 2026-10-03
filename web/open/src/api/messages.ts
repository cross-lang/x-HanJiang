import request from './request'
import type { PageResult } from '@/types/api'
import type { OpenMessage } from '@/types/message'

/**
 * 站内信接口（开放平台门户，/api/open-portal/v1/messages）。
 * 开发者站内信独立表 developer_messages，与管理端站内信分表隔离。
 */

/** 未读消息数（右上角铃铛角标） */
export function getUnreadCount() {
  return request.get<{ count: number }>('/messages/unread-count')
}

/** 站内信列表（分页，时间倒序） */
export function listMessages(params: { page: number; page_size: number }) {
  return request.get<PageResult<OpenMessage>>('/messages', { params })
}

/** 标记单条已读 */
export function markMessageRead(id: number) {
  return request.post<{ message: string }>(`/messages/${id}/read`)
}

/** 全部已读 */
export function markAllMessagesRead() {
  return request.post<{ message: string }>('/messages/read-all')
}
