/** 开放平台 scope 目录类型（与 server/src/constants/scopes.py 对齐） */

export interface OpenScope {
  id: number
  scope_code: string
  scope_name: string
  module: string
  module_label: string | null
  operation: string
  description: string | null
  sort_order: number
}
