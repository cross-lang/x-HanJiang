import request from './request'
import type { ApiDocEndpoint } from '@/types/apiDoc'

/**
 * 开放接口文档目录接口。
 * 现状：后端暂未提供文档元数据接口，前端 ApiDocs 页当前使用内置静态目录
 * （与本仓库 server/src/api/open/v1 的既有接口一一对应）；
 * 待后端提供统一文档接口（如 GET /docs/catalog）后切换为动态数据源。
 */
export function fetchApiDocs() {
  return request.get<ApiDocEndpoint[]>('/docs/catalog')
}
