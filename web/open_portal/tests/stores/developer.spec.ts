// 开发者登录态 store（src/stores/developer.ts）行为测试
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { getToken, getRefreshToken } from '@/utils/storage'
import { useDeveloperStore } from '@/stores/developer'

// 仅 mock 资料接口，真实走 storage / pinia 逻辑
const { getDeveloperProfileMock } = vi.hoisted(() => ({
  getDeveloperProfileMock: vi.fn(),
}))
vi.mock('@/api/developer', () => ({ getDeveloperProfile: getDeveloperProfileMock }))

describe('stores/developer 登录态', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    getDeveloperProfileMock.mockReset()
  })

  it('setToken 同时更新内存态与本地持久化令牌对', () => {
    const store = useDeveloperStore()
    store.setToken('access-1', 'refresh-1')
    expect(store.token).toBe('access-1')
    expect(store.refreshToken).toBe('refresh-1')
    // 持久化层同步写入
    expect(getToken()).toBe('access-1')
    expect(getRefreshToken()).toBe('refresh-1')
  })

  it('setToken 只传 access 时不刷新 refreshToken', () => {
    const store = useDeveloperStore()
    store.setToken('only-access')
    expect(store.token).toBe('only-access')
    expect(store.refreshToken).toBe('')
  })

  it('logout 清空内存态与本地令牌，且 profile 置空', () => {
    const store = useDeveloperStore()
    store.setToken('a', 'r')
    store.logout()
    expect(store.token).toBe('')
    expect(store.refreshToken).toBe('')
    expect(store.profile).toBeNull()
    expect(getToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
  })

  it('fetchProfile 拉取资料并写入 store', async () => {
    getDeveloperProfileMock.mockResolvedValue({ data: { id: 7, email: 'dev@hj.com', name: '夜雨' } })
    const store = useDeveloperStore()
    const profile = await store.fetchProfile()
    expect(getDeveloperProfileMock).toHaveBeenCalledTimes(1)
    expect(store.profile).toEqual({ id: 7, email: 'dev@hj.com', name: '夜雨' })
    expect(profile).toEqual({ id: 7, email: 'dev@hj.com', name: '夜雨' })
  })
})
