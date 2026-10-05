/** 开放平台类型（与 server/src/schemas/admin/openapi_app.py 对齐） */

export interface OpenAppItem {
  id: number
  app_id: string
  name: string
  description: string
  scopes: string[]
  status: string
  auth_mode: string
  rate_limit_per_minute: number
  owner_type: string
  owner_id: number | null
  owner_name: string | null
  /** 是否已通过创建审批（应用级授权状态，网关放行门槛） */
  approved: boolean
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

/** 开放应用申请（审批批次）项（与 server/src/schemas/admin/openapi_app_registration.py 对齐） */
export interface AppRegistrationItem {
  /** 申请ID（批次号，内部主键） */
  id: number
  /** 申请码：6位数字，对外展示用 */
  registration_code: string
  app_id: number
  app_id_str: string
  app_name: string
  owner_name: string | null
  /** 归属类型：developer 开发者自助 / admin 管理员分配 */
  owner_type: string
  /** 申请类型：create 创建申请 / update 修改申请 */
  registration_type: string
  name: string
  description: string
  scopes: string[]
  auth_mode: string
  apply_reason: string | null
  /** 审批状态：pending / approved / rejected */
  status: string
  approved_by: number | null
  approval_note: string | null
  approved_at: string | null
  created_at: string
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
