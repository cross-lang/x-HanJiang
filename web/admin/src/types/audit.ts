/** 审计日志 / 登录日志类型（与 server/src/schemas/audit.py、login_log.py 对齐） */

export interface AuditLogItem {
  id: number
  entity_type: string
  entity_id: string | null
  action: string
  operator_id: number | null
  operator_username: string | null
  operator_real_name: string | null
  before_data: Record<string, unknown> | null
  after_data: Record<string, unknown> | null
  ip_address: string | null
  created_at: string | null
  remarks: string | null
}

export interface LoginLogItem {
  id: number
  user_id: number | null
  username: string | null
  name: string | null
  login_type: string
  login_type_label: string
  ip_address: string | null
  status: string
  created_at: string | null
}
