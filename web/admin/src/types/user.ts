/** 用户管理相关类型（与 server/src/schemas/user.py 对齐） */

export interface UserItem {
  id: number
  username: string
  email: string
  name: string
  phone: string
  avatar_url: string | null
  roles: { id: number; role_name: string; role_code?: string }[]
  status: string
  gender: string
  birthday: string
  last_login_at: string | null
  last_login_ip: string | null
  created_at: string | null
  updated_at: string | null
}

export interface UserFormPayload {
  username: string
  name: string
  email: string
  phone: string
  birthday: string
  gender: string
  role_ids: number[]
  password: string
  status: string
}
