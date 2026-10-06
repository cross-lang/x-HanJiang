/** 仪表盘相关类型（与 server/src/services/dashboard_service.py 返回结构对齐） */ export interface NameValueItem {
  name: string
  value: number
}

export interface TrendSeries {
  dates: string[]
  counts: number[]
}

export interface NotifyTrend {
  dates: string[]
  success: number[]
  failed: number[]
}

export interface StorageUsage {
  total_size_bytes: number
  total_count: number
  by_folder: { folder: string; count: number; size_bytes: number }[]
}

export interface LoginLogBrief {
  id: number
  username: string
  name: string
  ip_address: string | null
  status: string
  created_at: string | null
}

export interface AuditLogBrief {
  id: number
  entity_type: string
  action: string
  ip_address: string | null
  created_at: string | null
}

/** 开放平台统计板块（与后端 service._build_openapi_stats 对齐） */
export interface OpenapiStats {
  cards: {
    app_total: number
    developer_count: number
    pending_registrations: number
    week_registrations: number
  }
  app_status_distribution: NameValueItem[]
  registration_status_distribution: NameValueItem[]
  registration_trend: { dates: string[]; submitted: number[]; reviewed: number[] }
  recent_registrations: {
    registration_code: string
    app_name: string
    registration_type: string
    status: string
    status_label: string
    owner_name: string
    created_at: string | null
  }[]
}

export interface DashboardStats {
  cards: {
    user_count: number
    role_count: number
    app_count: number
    today_login: number
  }
  login_trend: TrendSeries
  audit_trend: TrendSeries
  role_distribution: NameValueItem[]
  user_status_distribution: NameValueItem[]
  notify_channel_distribution: NameValueItem[]
  new_users_trend: TrendSeries
  login_failed_trend: TrendSeries
  notify_trend: NotifyTrend
  storage_usage: StorageUsage
  recent_logins: LoginLogBrief[]
  recent_audits: AuditLogBrief[]
  openapi: OpenapiStats
}

/** 系统监控：通知渠道健康度 + 服务器资源占用 */
export interface NotificationMonitor {
  stats: { total: number; success: number; failed: number; pending: number }
  channels: { channel: string; status: string }[]
  uptime?: { uptime_text?: string }
  cpu?: { percent: number; core_count: number; thread_count: number; status: string }
  memory?: { percent: number; used_gb: number; total_gb: number; status: string }
  disk?: { used_percent: number; used_gb: number; total_gb: number; status: string }
  network?: { recv_kbps: number; send_kbps: number; bytes_recv_total_mb: number; bytes_sent_total_mb: number }
}
