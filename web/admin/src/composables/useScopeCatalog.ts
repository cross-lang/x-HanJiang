/**
 * 开放平台 scope 目录 composable。
 *
 * scope 元数据的唯一事实来源是后端 OpenApiScopeCode 统一目录（启动时对账到
 * openapi_scopes 表），前端通过 listScopes() 拉取并做 code → 中文名映射，
 * 供应用列表「权限范围」列、应用表单勾选面板等展示场景复用。
 * 模块级缓存：同一会话内多次调用只请求一次。
 */
import { ref } from 'vue'
import { listScopes } from '@/api/openapi'
import type { OpenScope } from '@/types/openapi'

/** 模块级缓存：一次会话内所有调用方共享，避免重复请求 */
let cached: OpenScope[] | null = null

/** scope 编码 → 中文名映射（用于列表展示） */
const scopeNames = ref<Record<string, string>>({})

/** 完整 scope 目录（用于表单勾选面板） */
const scopeList = ref<OpenScope[]>([])

/** 拉取 scope 目录（带缓存；失败时静默降级为空目录，展示层回退为裸编码） */
export async function fetchScopes(): Promise<void> {
  if (cached) {
    scopeList.value = cached
    return
  }
  try {
    const res = await listScopes()
    cached = res.data
    scopeList.value = cached
    scopeNames.value = Object.fromEntries(cached.map(s => [s.scope_code, s.scope_name]))
  } catch {
    // 错误已由请求层处理；保留空目录，调用方自行降级
  }
}

/** 按 scope 编码取中文名（未命中回退为编码本身） */
export function scopeNameOf(code: string): string {
  return scopeNames.value[code] || code
}

/** 组合入口：返回目录状态与映射 */
export function useScopeCatalog() {
  return { scopeList, scopeNames, fetchScopes, scopeNameOf }
}
