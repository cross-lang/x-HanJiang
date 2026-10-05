import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getDeveloperProfile } from '@/api/developer'
import { clearToken, getToken, getRefreshToken, setRefreshToken, setToken as persistToken } from '@/utils/storage'
import type { DeveloperProfile } from '@/types/auth'

/** 开放平台门户登录态（开发者身份，有状态会话：access + refresh 令牌对） */
export const useDeveloperStore = defineStore('developer', () => {
  const profile = ref<DeveloperProfile | null>(null)
  const token = ref(getToken() || '')
  const refreshToken = ref(getRefreshToken() || '')

  /** 拉取当前开发者资料（路由守卫/布局挂载时调用；失败即登出） */
  async function fetchProfile(): Promise<DeveloperProfile | null> {
    const res = await getDeveloperProfile()
    profile.value = res.data
    return res.data
  }

  function setToken(t: string, rt?: string) {
    token.value = t
    persistToken(t)
    if (rt) {
      refreshToken.value = rt
      setRefreshToken(rt)
    }
  }

  function logout() {
    token.value = ''
    refreshToken.value = ''
    profile.value = null
    clearToken()
  }

  return { profile, token, refreshToken, fetchProfile, setToken, logout }
})
