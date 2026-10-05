import request from './request'
import type { PageResult } from '@/types/api'
import type {
  AppRegistrationItem,
  DeveloperItem,
  OpenAppCreatedResult,
  OpenAppFormPayload,
  OpenAppItem,
  OpenScope,
} from '@/types/openapi'

export interface OpenAppQuery {
  page: number
  page_size: number
  keyword?: string
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

export function updateAppStatus(id: number, status: string) {
  return request.put<OpenAppItem>(`/apps/${id}/status`, { status })
}

export function rotateAppKey(id: number) {
  return request.post<{ app_id: string; app_key: string }>(`/apps/${id}/rotate-key`)
}

export function deleteApp(id: number) {
  return request.delete<{ message: string }>(`/apps/${id}`)
}

export interface AppRegistrationQuery {
  page: number
  page_size: number
  keyword?: string
  /** 申请类型过滤：create 创建申请 / update 修改申请 */
  registration_type?: string
  /** 审批状态过滤：pending / approved / rejected */
  status?: string
}

/** 应用申请（审批批次）分页列表（管理端"开放平台 → 应用审批"） */
export function listAppRegistrations(params: AppRegistrationQuery) {
  return request.get<PageResult<AppRegistrationItem>>('/app-registrations', { params })
}

/** 应用申请详情（按申请ID） */
export function getAppRegistration(id: number) {
  return request.get<AppRegistrationItem>(`/app-registrations/${id}`)
}

/** 审批应用申请：approved=true 通过 / false 驳回，note 为审批意见 */
export function reviewAppRegistration(id: number, data: { approved: boolean; note?: string }) {
  return request.put<AppRegistrationItem>(`/app-registrations/${id}/approval`, data)
}

export interface DeveloperQuery {
  page: number
  page_size: number
  keyword?: string
  /** 账号状态过滤：enabled / disabled */
  status?: string
}

/** 开发者用户分页列表（管理端"开放平台 → 开发者管理"） */
export function listDevelopers(params: DeveloperQuery) {
  return request.get<PageResult<DeveloperItem>>('/developers', { params })
}

export interface DeveloperAppsQuery {
  page: number
  page_size: number
  keyword?: string
}

/** 开发者名下开放应用分页列表 */
export function listDeveloperApps(developerId: number, params: DeveloperAppsQuery) {
  return request.get<PageResult<OpenAppItem>>(`/developers/${developerId}/apps`, { params })
}
