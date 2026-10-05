import request from './request'
import type { PageResult } from '@/types/api'
import type { DeveloperItem, OpenAppItem, OpenAppCreatedResult, OpenScope, OpenAppFormPayload } from '@/types/openapi'

export interface OpenAppQuery {
  page: number
  page_size: number
  keyword?: string
  /** 管理端个人视角类目：created 我新建的 / approved 我审批的 */
  scope?: 'created' | 'approved'
}

export function listApps(params: OpenAppQuery) {
  return request.get<PageResult<OpenAppItem>>('/apps', { params })
}

export function listScopes() {
  return request.get<OpenScope[]>('/apps/scopes')
}

export function createApp(data: OpenAppFormPayload) {
  return request.post<OpenAppCreatedResult>('/apps', data)
}

export function updateApp(id: number, data: Partial<OpenAppFormPayload>) {
  return request.put<OpenAppItem>(`/apps/${id}`, data)
}

/** 审批开发者 scope 申请：approved=true 通过 / false 驳回，note 为审批意见（驳回必填） */
export function updateApproval(id: number, data: { approved: boolean; note?: string }) {
  return request.put<OpenAppItem>(`/apps/${id}/approval`, data)
}

export function updateAppStatus(id: number, status: string) {
  return request.put<OpenAppItem>(`/apps/${id}/status`, { status })
}

export function rotateAppKey(id: number) {
  return request.post<{ app_id: string; app_key: string }>(`/apps/${id}/rotate-key`)
}

export function deleteApp(id: number) {
  return request.delete<{ message: string }>(`/apps/${id}`)
}

export interface DeveloperQuery {
  page: number
  page_size: number
  keyword?: string
  /** 账号状态过滤：enabled / disabled */
  status?: string
}

/** 开发者用户分页列表（管理端"开放平台 → 用户管理"） */
export function listDevelopers(params: DeveloperQuery) {
  return request.get<PageResult<DeveloperItem>>('/admin/developers', { params })
}

export interface DeveloperAppsQuery {
  page: number
  page_size: number
  keyword?: string
}

/** 开发者名下开放应用分页列表 */
export function listDeveloperApps(developerId: number, params: DeveloperAppsQuery) {
  return request.get<PageResult<OpenAppItem>>(`/admin/developers/${developerId}/apps`, { params })
}
