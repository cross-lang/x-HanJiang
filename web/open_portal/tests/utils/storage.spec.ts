// 本地存储工具（src/utils/storage.ts）行为测试：键名收敛、读写与清理
import { describe, it, expect, beforeEach } from 'vitest'
import {
  getToken,
  setToken,
  getRefreshToken,
  setRefreshToken,
  clearToken,
  getStorageJson,
  setStorageJson,
  removeStorage,
} from '@/utils/storage'

describe('utils/storage 登录态令牌读写', () => {
  beforeEach(() => {
    // 每个用例前清空 happy-dom 提供的 localStorage，保证隔离
    localStorage.clear()
  })

  it('setToken / getToken 可往返存取访问令牌', () => {
    setToken('access-abc')
    expect(getToken()).toBe('access-abc')
  })

  it('setRefreshToken / getRefreshToken 可往返存取刷新令牌', () => {
    setRefreshToken('refresh-xyz')
    expect(getRefreshToken()).toBe('refresh-xyz')
  })

  it('clearToken 同时移除访问令牌与刷新令牌', () => {
    setToken('access-abc')
    setRefreshToken('refresh-xyz')
    clearToken()
    expect(getToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
  })

  it('setStorageJson / getStorageJson 可往返存取对象', () => {
    setStorageJson('demo_obj', { a: 1, name: '夜雨' })
    expect(getStorageJson<{ a: number; name: string }>('demo_obj')).toEqual({ a: 1, name: '夜雨' })
  })

  it('getStorageJson 在存储损坏时安全返回 null，不抛异常', () => {
    localStorage.setItem('bad_json', '{{{ not json')
    expect(getStorageJson('bad_json')).toBeNull()
  })

  it('removeStorage 删除指定键', () => {
    setStorageJson('temp', 123)
    expect(getStorageJson('temp')).toBe(123)
    removeStorage('temp')
    expect(getStorageJson('temp')).toBeNull()
  })
})
