/** 开放平台应用类型（与 server/src/schemas/openapi_app.py 对齐） */

export interface OpenAppItem {
  id: number
  app_id: string
  name: string
  description: string
  scopes: string[]
  status: string
  auth_mode: string
  rate_limit_per_minute: number
  /** 审批状态：pending 待审批 / approved 已通过 / rejected 已驳回 */
  approval_status: string
  approval_note: string | null
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
