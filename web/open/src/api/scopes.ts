import request from './request'
import type { OpenScope } from '@/types/scope'

/**
 * 开放平台 scope 目录接口（门户侧）。
 * scope 元数据唯一事实来源为后端 OpenApiScopeCode 目录（启动时对账到
 * openapi_scopes 表）；目录接口挂载于 /api/open-portal/v1/scopes
 * （独立 scopes_router，避免被 /apps/{app_id} 抢先匹配）。
 */
export function listScopes() {
  return request.get<OpenScope[]>('/scopes')
}
