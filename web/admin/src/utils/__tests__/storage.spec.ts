/**
 * 本地存储工具行为测试（happy-dom 提供 localStorage）。
 * 覆盖 token 读写/清除、JSON 存取、损坏数据兜底、按键删除。
 */
import { beforeEach, describe, expect, it } from 'vitest'
import { getToken, setToken, clearToken, getStorageJson, setStorageJson, removeStorage } from '../storage'

beforeEach(() => {
  // 每个用例从干净的本地存储开始，避免键值残留串扰
  localStorage.clear()
})

describe('token 存取', () => {
  it('setToken 写入后 getToken 能读回同一值', () => {
    setToken('access-abc')
    expect(getToken()).toBe('access-abc')
  })

  it('clearToken 清除后 getToken 返回 null', () => {
    setToken('access-abc')
    clearToken()
    expect(getToken()).toBeNull()
  })

  it('从未写入时 getToken 返回 null', () => {
    expect(getToken()).toBeNull()
  })
})

describe('JSON 存取', () => {
  it('setStorageJson 写入对象，getStorageJson 读回等价对象', () => {
    setStorageJson('user_pref', { theme: 'dark', lang: 'zh' })
    expect(getStorageJson<{ theme: string; lang: string }>('user_pref')).toEqual({
      theme: 'dark',
      lang: 'zh',
    })
  })

  it('键不存在时 getStorageJson 返回 null', () => {
    expect(getStorageJson('missing')).toBeNull()
  })

  it('存储内容损坏（非法 JSON）时 getStorageJson 兜底返回 null 而非抛错', () => {
    localStorage.setItem('broken', '{oops')
    expect(getStorageJson('broken')).toBeNull()
  })

  it('removeStorage 移除指定键', () => {
    setStorageJson('tmp', { a: 1 })
    removeStorage('tmp')
    expect(getStorageJson('tmp')).toBeNull()
  })
})
