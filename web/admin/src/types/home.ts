/** 首页相关类型（与 server/src/services/dashboard_service.py 的 my_activity 返回结构对齐） */

export interface MyActivity {
  recent_logins: {
    id: number
    ip_address: string | null
    login_type: string
    login_type_label: string
    status: string
    created_at: string | null
  }[]
  recent_audits: {
    id: number
    entity_type: string
    action: string
    ip_address: string | null
    created_at: string | null
  }[]
}
