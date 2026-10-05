/** 开放平台应用类型（与 server/src/schemas/open_portal/app.py 对齐） */

export interface OpenAppItem {
  id: number
  app_id: string
  name: string
  description: string
  scopes: string[]
  status: string
  auth_mode: string
  rate_limit_per_minute: number
  /** 是否已授权（网关放行门槛；创建申请审批通过后为 true） */
  approved: boolean
  /** 派生审批状态：pending 待审批 / approved 已通过 / rejected 已驳回 / null 未申请过 */
  approval_status: string | null
  /** 存在待审批申请时的申请ID（批次号），无则 null */
  pending_registration_id: number | null
  last_used_at: string | null
  created_at: string
  updated_at: string
}

export interface OpenAppCreatedResult {
  id?: number
  app_id: string
  name: string
  scopes: string[]
  auth_mode: string
  app_key: string
}

export interface OpenAppFormPayload {
  name: string
  description: string
  auth_mode: string
  scopes: string[]
  rate_limit_per_minute?: number
}

/** scope 申请（新增申请 / 调整申请） */
export interface ScopeApplyPayload {
  scopes: string[]
  /** 申请说明（管理员审批依据） */
  reason?: string
}

/** 应用审批记录（对应 openapi_app_registrations 批次：每次申请一条记录） */
export interface OpenAppApproval {
  id: number
  /** 申请码：6位数字，对外展示用 */
  registration_code: string
  app_id: number
  /** 申请类型：create 创建申请 / update 修改申请 */
  registration_type: string
  name: string
  description: string
  scopes: string[]
  auth_mode: string
  /** 申请说明/用途 */
  reason: string | null
  /** pending 待审批 / approved 已通过 / rejected 已驳回 */
  status: string
  /** 审批人姓名 */
  approver_name: string | null
  /** 审批意见/驳回原因 */
  note: string | null
  created_at: string
  reviewed_at: string | null
}
