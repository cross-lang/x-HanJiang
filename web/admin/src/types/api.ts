/** 后端统一响应包裹（与 server/src/api/response.py 对齐） */
export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
  timestamp: string
  request_id: string | null
}

/** 分页响应结构（与后端 PaginatedResponse 对齐） */
export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}
