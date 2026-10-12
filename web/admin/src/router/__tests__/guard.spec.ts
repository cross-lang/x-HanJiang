/**
 * 全局路由守卫行为测试（使用 src/router/index.ts 导出的真实 router）。
 *
 * 被测守卫规则（见 router/index.ts beforeEach）：
 *  1. 无 token：仅放行公共路径 /login，其余一律跳 /login；
 *  2. 有 token 访问 /login：回首页；
 *  3. 权限未加载时先 fetchUserInfo；
 *  4. 目标路由声明 meta.perm 而当前用户无该权限：重定向兜底 /profile。
 *
 * 为避免跨用例的"重复导航短路"，每次 push 都带唯一 query（守卫只看 to.path，query 不影响判定）；
 * 视图组件全部打桩，本用例只验证守卫的导航决策，不渲染任何业务页面（避免引入 echarts 等重型模块）。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// 打桩业务视图：守卫只关心 to.path / meta.perm，组件本身无需真实渲染
vi.mock('@/views/login/Login.vue', () => ({ default: { name: 'LoginStub', setup: () => null } }))
vi.mock('@/views/layout/Layout.vue', () => ({ default: { name: 'LayoutStub', setup: () => null } }))
vi.mock('@/views/dashboard/Dashboard.vue', () => ({ default: { name: 'DashboardStub', setup: () => null } }))
vi.mock('@/views/profile/Profile.vue', () => ({ default: { name: 'ProfileStub', setup: () => null } }))
vi.mock('@/views/system/UserList.vue', () => ({ default: { name: 'UserListStub', setup: () => null } }))

// mock 鉴权 API，控制守卫内 fetchUserInfo 返回的权限列表
vi.mock('@/api/auth', () => ({
  getCurrentUser: vi.fn(),
  getMenus: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
}))

import router from '../index'
import { getCurrentUser } from '@/api/auth'
import { getToken, setToken } from '@/utils/storage'

const mockGetCurrentUser = vi.mocked(getCurrentUser)

/** 让守卫拉取到指定权限列表 */
function mockPermissions(perms: string[]) {
  mockGetCurrentUser.mockResolvedValue({
    data: { permissions: perms },
  } as unknown as Awaited<ReturnType<typeof getCurrentUser>>)
}

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
  mockGetCurrentUser.mockReset()
})

describe('路由守卫：登录态与权限拦截', () => {
  it('未登录访问受保护路由 /users 被重定向到 /login', async () => {
    expect(getToken()).toBeNull()
    await router.push('/users?case=1')
    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('未登录访问公共路由 /login 直接放行', async () => {
    await router.push('/login?case=2')
    expect(router.currentRoute.value.path).toBe('/login')
  })

  it('已登录访问 /login 被重定向回首页 /home', async () => {
    setToken('fake-token')
    mockPermissions(['*'])
    await router.push('/login?case=3')
    // /login → 守卫返回 '/' → 重定向 '/home'（home:view 因 * 放行）
    expect(router.currentRoute.value.path).toBe('/home')
  })

  it('目标路由要求 home:view 而用户无该权限时，兜底重定向到 /profile', async () => {
    setToken('fake-token')
    // 权限列表里没有 home:view
    mockPermissions(['other:perm'])
    await router.push('/home?case=4')
    expect(router.currentRoute.value.path).toBe('/profile')
  })

  it('用户拥有 home:view 权限时可正常进入首页', async () => {
    setToken('fake-token')
    mockPermissions(['home:view'])
    await router.push('/home?case=5')
    expect(router.currentRoute.value.path).toBe('/home')
  })
})
