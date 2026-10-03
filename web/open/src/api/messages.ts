import request from './request'
import type { PageResult } from '@/types/api'
import type { OpenMessage } from '@/types/message'

/**
 * 站内信接口（预留）。
 * 现状：开发者站内信为规划中的功能模块，接口前端已接入、后端待实现。
 */
export function listMessages(params: { page: number; page_size: number }) {
  return request.get<PageResult<OpenMessage>>('/messages', { params })
}

/** 标记消息已读 */
export function markMessageRead(id: number) {
  return request.post<{ message: string }>(`/messages/${id}/read`)
}
