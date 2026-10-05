/** 开放能力接口文档类型（对齐 WPS 开放平台文档样式：API说明 / 请求说明 / Headers / Query / 请求示例 / 响应体 / 响应示例） */

/** 请求头 / 请求参数 / 响应字段共用行结构 */
export interface ApiParamRow {
  name: string
  type: string
  required: boolean
  /** 可选值（如 normal：普通用户组；无则 '-'） */
  values?: string
  /** 限制（如 最大100；无则 '-'） */
  limit?: string
  /** 示例值（无则 '-'） */
  example?: string
  /** 描述 */
  desc: string
}

/** 开放能力接口详情 */
export interface CapabilityApi {
  id: string
  name: string
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  /** 接口路径（不含域名与 /api/open/v1 前缀，展示时拼接） */
  path: string
  /** 权限要求（scope 码；无需 scope 时为 '仅需有效应用凭证'） */
  scope: string
  /** 一句话说明（API 说明区） */
  summary: string
  /** 注意事项 */
  notes: string[]
  /** 使用限制 */
  limits: string[]
  /** 请求头（统一公共头 + 接口特殊头） */
  headers: ApiParamRow[]
  /** 查询参数（Query） */
  query: ApiParamRow[]
  /** 路径参数（Path） */
  pathParams: ApiParamRow[]
  /** 请求体参数（Body，无 body 的接口为空数组） */
  body: ApiParamRow[]
  /** 请求示例（cURL，hmac 签名模式） */
  curl: string
  /** 响应体字段（含公共结构） */
  responseFields: ApiParamRow[]
  /** 响应示例（JSON 文本） */
  responseExample: string
  /** 响应说明 */
  responseDesc: string
}

/** 开放能力模块（一级菜单"开放能力"下的二级菜单） */
export interface CapabilityModule {
  /** 路由参数，对应 /capability/:module */
  key: 'user' | 'role' | 'file' | 'app' | 'health'
  name: string
  desc: string
  apis: CapabilityApi[]
}
