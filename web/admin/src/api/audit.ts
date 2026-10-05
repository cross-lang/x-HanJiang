import request from './request'
import type { PageResult } from '@/types/api'
import type { AuditLogItem, LoginLogItem } from '@/types/audit'

export interface AuditQuery {
  page: number
  page_size: number
  keyword?: string
  /** 审计日志：只看指定操作者 */
  operator_id?: number
  /** 登录日志：只看指定用户 */
  user_id?: number
}

/** 审计日志列表 */
export function listAuditLogs(params: AuditQuery) {
  return request.get<PageResult<AuditLogItem>>('/logs/audit', { params })
}

/** 登录日志列表 */
export function listLoginLogs(params: AuditQuery) {
  return request.get<PageResult<LoginLogItem>>('/logs/login', { params })
}

/** 审计日志详情 */
export function getAuditLogDetail(id: number) {
  return request.get<AuditLogItem>(`/logs/audit/${id}`)
}

/** 登录日志详情 */
export function getLoginLogDetail(id: number) {
  return request.get<LoginLogItem>(`/logs/login/${id}`)
}

/** 导出审计日志 CSV（原始 fetch，后端直接返回文件流） */
export function exportAuditCsv(params: { keyword?: string }): Promise<Response> {
  const query = new URLSearchParams()
  if (params.keyword) query.set('keyword', params.keyword)
  const suffix = query.toString()
  const token = localStorage.getItem('access_token')
  return fetch(`/api/v1/logs/audit/export${suffix ? `?${suffix}` : ''}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
}

/** 导出登录日志 CSV（原始 fetch，后端直接返回文件流） */
export function exportLoginLogCsv(params: { keyword?: string }): Promise<Response> {
  const query = new URLSearchParams()
  if (params.keyword) query.set('keyword', params.keyword)
  const suffix = query.toString()
  const token = localStorage.getItem('access_token')
  return fetch(`/api/v1/logs/login/export${suffix ? `?${suffix}` : ''}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
}
