/** 开放接口文档类型（接口目录展示：路径/方法/鉴权/签名/入参/返参） */

export interface ApiDocParameter {
  name: string
  location: 'header' | 'query' | 'path' | 'body'
  required: boolean
  type: string
  description: string
}

export interface ApiDocEndpoint {
  id: string
  /** 所属模块（用户管理 / 应用信息 …） */
  module: string
  /** 接口名称（如：开放平台用户列表） */
  name: string
  /** 请求路径（不含 /api/open/v1 前缀的展示值） */
  path: string
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  /** 鉴权方式：app-key 明文 / hmac 签名 */
  auth_mode: 'app-key' | 'hmac'
  /** 所需 scope（如 user:read），为空表示无需 scope */
  scope: string
  /** 入参 */
  params: ApiDocParameter[]
  /** 返参示例（JSON 字符串，前端格式化展示） */
  response_example: string
  /** 返回说明 */
  response_desc: string
  description: string
}
