/** 角色与权限管理类型（与 server/src/schemas/role.py 对齐） */

export interface RoleItem {
  id: number
  role_name: string
  role_code: string
  description: string | null
  role_type: string
  status: string
  created_at: string | null
  updated_at: string | null
}

export interface PermissionItem {
  id: number
  perm_code: string
  perm_name: string
  module: string
  module_label: string
  operation: string
  description: string | null
  sort_order: number
  is_deprecated?: boolean
}

export interface RolePermissionRelation {
  role_id: number
  permission: PermissionItem
}
