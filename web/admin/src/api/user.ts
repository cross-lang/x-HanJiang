import request from './request'
import type { PageResult } from '@/types/api'
import type { UserItem, UserFormPayload } from '@/types/user'

export interface UserQuery {
  page: number
  page_size: number
  keyword?: string
  status?: string
}

export function listUsers(params: UserQuery) {
  return request.get<PageResult<UserItem>>('/users', { params })
}

export function createUser(data: UserFormPayload & { role_ids: number[] }) {
  return request.post<UserItem>('/users', data)
}

export function updateUser(id: number, data: Partial<UserFormPayload>) {
  return request.post<UserItem>(`/users/${id}/update`, data)
}

export function resetUserPassword(id: number, newPassword: string) {
  return request.post<{ message: string }>(`/users/${id}/reset-password`, {
    new_password: newPassword,
    confirm_password: newPassword,
  })
}

export function deleteUser(id: number) {
  return request.post<{ message: string }>(`/users/${id}/delete`)
}

/** 导出用户 CSV（原始 fetch，返回 Blob，调用方负责下载） */
export function exportUsersCsv(params: { keyword?: string; status?: string }): Promise<Response> {
  const query = new URLSearchParams()
  if (params.keyword) query.set('keyword', params.keyword)
  if (params.status) query.set('status', params.status)
  const token = localStorage.getItem('access_token')
  return fetch(`/api/v1/users/export?${query.toString()}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
}
