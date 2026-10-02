import request from './request'
import type { PageResult } from '@/types/api'
import type { PermissionItem } from '@/types/role'

export function listPermissions(params: { page: number; page_size: number; keyword?: string }) {
  return request.get<PageResult<PermissionItem>>('/permissions', { params })
}
