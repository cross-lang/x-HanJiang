import request from './request'
import type { PageResult } from '@/types/api'
import type {
  OpenAppApproval,
  OpenAppCreatedResult,
  OpenAppFormPayload,
  OpenAppItem,
  ScopeApplyPayload,
} from '@/types/app'

/**
 * 开发者应用管理接口（门户侧）。
 * 现状：应用管理的归属（owner=开发者）与审批流为规划中的开放平台闭环，
 * 以下接口前端已接入、后端待实现；管理端审批能力（/api/admin/v1/apps）已存在。
 */

export interface OpenAppQuery {
  page: number
  page_size: number
  keyword?: string
}

/** 我的应用列表（分页） */
export function listMyApps(params: OpenAppQuery) {
  return request.get<PageResult<OpenAppItem>>('/apps', { params })
}

/** 创建应用 */
export function createApp(data: OpenAppFormPayload) {
  return request.post<OpenAppCreatedResult>('/apps', data)
}

/** 更新应用基本信息 */
export function updateApp(id: number, data: Partial<OpenAppFormPayload>) {
  return request.put<OpenAppItem>(`/apps/${id}`, data)
}

/** 删除应用 */
export function deleteApp(id: number) {
  return request.delete<{ deleted: boolean }>(`/apps/${id}`)
}

/** 重置 App Key */
export function rotateAppKey(id: number) {
  return request.post<{ app_id: string; app_key: string }>(`/apps/${id}/rotate-key`)
}

/** 申请/调整 scope（提交后进入管理员审批） */
export function applyAppScopes(id: number, data: ScopeApplyPayload) {
  return request.put<OpenAppItem>(`/apps/${id}/scopes`, data)
}

/** 应用审批记录（全部申请/审批历史，最新在前） */
export function listAppApprovals(id: number) {
  return request.get<OpenAppApproval[]>(`/apps/${id}/approvals`)
}
