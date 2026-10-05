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
  owner_name: string | null
  /** 审批状态：pending / approved / rejected；管理端自建应用为 null（无审批概念） */
  approval_status: string | null
  /** 审批人用户 ID（管理系统 users.id），未审批为 null */
  approved_by: number | null
  /** 审批意见（驳回原因等） */
  approval_note: string | null
  /** 开发者提交 scope 申请时的申请理由 */
  scope_apply_reason: string | null
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

/** 开放平台开发者用户（管理端"用户管理"列表项） */
export interface DeveloperItem {
  id: number
  username: string
  email: string
  name: string
  phone: string
  /** 认证类型：personal 个人 / enterprise 企业 */
  certification_type: string | null
  /** 认证状态：none / pending / approved / rejected */
  certification_status: string
  company_name: string | null
  /** 账号状态：enabled / disabled */
  status: string
  /** 旗下开放应用数量（不含已软删除） */
  app_count: number
  last_login_at: string | null
  created_at: string
}

export interface OpenAppFormPayload {
  name: string
  description: string
  auth_mode: string
  scopes: string[]
}
