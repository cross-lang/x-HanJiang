/** 登录 / 当前用户 / 菜单相关类型（与 server/src/schemas/auth.py、menu 接口对齐） */

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResult {
  access_token: string
  refresh_token?: string
  token_type?: string
  expires_in?: number
}

export interface UserRoleBrief {
  id: number
  role_name: string
  role_code: string
}

/** 个人中心展示用权限（含模块分组信息） */
export interface ProfilePermission {
  module: string
  module_label: string | null
  code: string
  name: string
}

/** 当前登录用户信息（/auth/me 返回） */
export interface UserInfo {
  id: number
  username: string
  email: string
  name: string | null
  role_code: string | null
  status: string
  avatar_url: string | null
  phone: string | null
  birthday: string | null
  gender: string | null
  last_login_at: string | null
  permissions: string[]
  roles?: UserRoleBrief[]
  permission_list?: ProfilePermission[]
}

export interface MenuItem {
  id: number
  parent_id: number | null
  title: string
  path: string
  icon: string | null
  perm_code: string | null
  sort_order: number
  type: 'menu' | 'directory'
  children?: MenuItem[]
}
