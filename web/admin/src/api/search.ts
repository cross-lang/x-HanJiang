import request from './request'
import type { SearchResult } from '@/types/search'

/** 全局搜索（按模块分组返回命中结果） */
export function search(keyword: string, limit = 5) {
  return request.get<SearchResult>('/search', { params: { keyword, limit } })
}
