/** 开放平台类型（与 server/src/schemas/openapi_app.py 对齐） */

export interface OpenAppItem {
  id: number
  app_id: string
  name: string
  description: string
  scopes: string[]
  status: string
  auth_mode: string
  rate_limit_per_minute: number
  owner_user_id: number | null
  owner_name: string | null
  last_used_at: string | null
  created_at: string
}

export interface OpenAppCreatedResult {
  id?: number
  app_id: string
  name: string
  scopes: string[]
  auth_mode: string
  app_key: string
}

export interface OpenScope {
  id: number
  scope_code: string
  scope_name: string
  module: string
  module_label: string | null
  operation: string
  description: string | null
}

export interface OpenAppFormPayload {
  name: string
  description: string
  auth_mode: string
  scopes: string[]
}
