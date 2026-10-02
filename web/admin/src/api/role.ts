import request from './request'
import type { PageResult } from '@/types/api'
import type { RoleItem, PermissionItem, RolePermissionRelation } from '@/types/role'

export function listRoles(params?: { page?: number; page_size?: number; keyword?: string }) {
  return request.get<PageResult<RoleItem> | RoleItem[]>('/roles', { params })
}

export function createRole(data: { role_name: string; role_code: string; description?: string; status?: string }) {
  return request.post<RoleItem>('/roles', data)
}

export function updateRole(id: number, data: Partial<{ role_name: string; description: string; status: string }>) {
  return request.post<RoleItem>(`/roles/${id}/update`, data)
}

export function deleteRole(id: number) {
  return request.post<{ message: string }>(`/roles/${id}/delete`)
}

export function listAllPermissions() {
  return request.get<PermissionItem[]>('/permissions', { params: { page: 1, page_size: 200 } })
}

export function listRolePermissions(roleId: number) {
  return request.get<RolePermissionRelation[]>(`/roles/${roleId}/permissions`)
}

export function bindRolePermission(roleId: number, permissionId: number) {
  return request.post(`/roles/${roleId}/permissions`, { permission_id: permissionId })
}

export function unbindRolePermission(roleId: number, permissionId: number) {
  return request.post(`/roles/${roleId}/permissions/${permissionId}/unbind`)
}
