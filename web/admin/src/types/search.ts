/** 全局搜索类型（与 server/src/services/search_service.py 返回结构对齐） */

export interface SearchHit {
  id: number
  title: string
  subtitle?: string
  path: string
  snippet?: string
  [key: string]: unknown
}

/** 搜索结果按模块分组：{ 模块名: 命中列表 } */
export type SearchResult = Record<string, SearchHit[]>
