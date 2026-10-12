/**
 * user store 行为测试（使用真实 pinia，每个用例注入全新实例）。
 * 覆盖：通配权限 *、精确权限命中/未命中、setToken 持久化、fetchUserInfo 回填权限、
 * logout 全量清理（含 localStorage 中的 token 与会话 id）。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// mock 鉴权 API，使 store 的异步方法不发真实网络请求
vi.mock('@/api/auth', () => ({
  getCurrentUser: vi.fn(),
  getMenus: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
}))

import { useUserStore } from '../user'
import { getCurrentUser } from '@/api/auth'
import { getToken } from '@/utils/storage'

const mockGetCurrentUser = vi.mocked(getCurrentUser)

beforeEach(() => {
  // 全新 pinia + 清空本地态，保证用例间互不污染
  setActivePinia(createPinia())
  localStorage.clear()
  mockGetCurrentUser.mockReset()
})

describe('hasPerm 权限判定', () => {
  it('拥有通配权限 * 时任意权限码都放行', () => {
    const store = useUserStore()
    store.permissions = ['*']
    expect(store.hasPerm('home:view')).toBe(true)
    expect(store.hasPerm('anything:else')).toBe(true)
  })

  it('权限码精确命中返回 true，未命中返回 false', () => {
    const store = useUserStore()
    store.permissions = ['user:view', 'role:edit']
    expect(store.hasPerm('user:view')).toBe(true)
    expect(store.hasPerm('role:edit')).toBe(true)
    expect(store.hasPerm('user:delete')).toBe(false)
  })

  it('权限列表为空时任何权限都不通过', () => {
    const store = useUserStore()
    store.permissions = []
    expect(store.hasPerm('home:view')).toBe(false)
  })
})

describe('setToken 持久化', () => {
  it('setToken 同时更新内存 token 与 localStorage', () => {
    const store = useUserStore()
    store.setToken('tok-123')
    expect(store.token).toBe('tok-123')
    expect(getToken()).toBe('tok-123')
  })
})

describe('fetchUserInfo 回填', () => {
  it('拉取成功后写入 userInfo 与 permissions', async () => {
    mockGetCurrentUser.mockResolvedValue({
      data: { username: 'john', permissions: ['a:view', 'b:edit'] },
    } as unknown as Awaited<ReturnType<typeof getCurrentUser>>)

    const store = useUserStore()
    await store.fetchUserInfo()

    expect(store.userInfo?.username).toBe('john')
    expect(store.permissions).toEqual(['a:view', 'b:edit'])
  })
})

describe('logout 清理', () => {
  it('登出后清空 token、用户、权限，并移除本地 token 与会话 id', async () => {
    const store = useUserStore()
    store.setToken('tok-to-clear')
    store.permissions = ['a:view']
    localStorage.setItem('ai_conversation_id', 'conv-1')

    store.logout()

    expect(store.token).toBe('')
    expect(store.userInfo).toBeNull()
    expect(store.permissions).toEqual([])
    expect(getToken()).toBeNull()
    expect(localStorage.getItem('ai_conversation_id')).toBeNull()
  })
})
