import request from './request'
import type { PageResult } from '@/types/api'
import type { OpenAppItem, OpenAppCreatedResult, OpenScope, OpenAppFormPayload } from '@/types/openapi'

export interface OpenAppQuery {
  page: number
  page_size: number
  keyword?: string
}

export function listApps(params: OpenAppQuery) {
  return request.get<PageResult<OpenAppItem>>('/admin/apps', { params })
}

export function listScopes() {
  return request.get<OpenScope[]>('/admin/apps/scopes')
}

export function createApp(data: OpenAppFormPayload) {
  return request.post<OpenAppCreatedResult>('/admin/apps', data)
}

export function updateApp(id: number, data: Partial<OpenAppFormPayload>) {
  return request.put<OpenAppItem>(`/admin/apps/${id}`, data)
}

/** 审批开发者 scope 申请：approved=true 通过 / false 驳回，note 为审批意见（驳回必填） */
export function updateApproval(id: number, data: { approved: boolean; note?: string }) {
  return request.put<OpenAppItem>(`/admin/apps/${id}/approval`, data)
}

export function updateAppStatus(id: number, status: string) {
  return request.put<OpenAppItem>(`/admin/apps/${id}/status`, { status })
}

export function rotateAppKey(id: number) {
  return request.post<{ app_id: string; app_key: string }>(`/admin/apps/${id}/rotate-key`)
}

export function deleteApp(id: number) {
  return request.delete<{ message: string }>(`/admin/apps/${id}`)
}
