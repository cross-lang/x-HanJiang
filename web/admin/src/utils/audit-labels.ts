/**
 * 审计日志"实体/操作"中文描述映射（展示层专用）。
 *
 * 后端审计日志只持久化英文编码（entity_type = PermissionModule.mark，
 * action = PermissionAction.mark / AuditAction.mark，见 server/src/constants/）。
 * 本模块为展示层统一提供「编码（中文描述）」格式化：
 *  - user → user（用户）
 *  - create → create（创建）
 * 未命中的编码原样返回，保证新增枚举无需改动调用方。
 */

/** 审计实体编码 → 中文描述（与后端 PermissionModule 对齐） */
export const AUDIT_ENTITY_LABELS: Readonly<Record<string, string>> = {
  user: '用户',
  role: '角色',
  permission: '权限',
  file: '文件',
  notification: '通知',
  announcement: '公告',
  alert: '告警',
  maintenance: '维护',
  openapi_app: '开放应用',
  openapi_app_registration: '应用申请',
  openapi_scope: '开放权限',
  dashboard: '仪表盘',
  swagger: '接口文档',
  profile: '个人中心',
  station: '站内信',
  search: '全局搜索',
  assistant: 'AI助手',
  audit_log: '审计日志',
  login_log: '登录日志',
}

/** 审计动作编码 → 中文描述（与后端 PermissionAction / AuditAction 对齐） */
export const AUDIT_ACTION_LABELS: Readonly<Record<string, string>> = {
  view: '查看',
  create: '创建',
  edit: '修改',
  update: '更新',
  delete: '删除',
  export: '导出',
  import: '导入',
  upload: '上传',
  download: '下载',
  publish: '发布',
  unpublish: '下架',
  withdraw: '撤回',
  bind_permission: '绑定权限',
  unbind_permission: '解绑权限',
  login: '登录',
  logout: '退出登录',
  status: '启停',
  approve: '审批',
  reject: '驳回',
  navigate: '跳转',
  scopes: '配置范围',
  rotate_key: '重置密钥',
  password: '修改密码',
  email: '更换邮箱',
  phone: '更换手机号',
  permission: '权限配置',
  config: '配置',
  search: '搜索',
  send: '发送',
  broadcast: '广播',
  chat: '对话',
  conversation: '会话管理',
  feedback: '反馈',
}

/** 实体编码 → "编码（中文）"，未命中原样返回 */
export function formatAuditEntity(code: string): string {
  const label = AUDIT_ENTITY_LABELS[code]
  return label ? `${code}（${label}）` : code
}

/** 操作编码 → "编码（中文）"，未命中原样返回 */
export function formatAuditAction(code: string): string {
  const label = AUDIT_ACTION_LABELS[code]
  return label ? `${code}（${label}）` : code
}
