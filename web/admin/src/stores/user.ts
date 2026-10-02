import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getCurrentUser, getMenus } from '@/api/auth'
import { clearToken, getToken, setToken as persistToken } from '@/utils/storage'
import type { MenuItem, UserInfo } from '@/types/auth'

export const useUserStore = defineStore('user', () => {
  const userInfo = ref<UserInfo | null>(null)
  const token = ref(getToken() || '')
  const menus = ref<MenuItem[]>([])
  const permissions = ref<string[]>([])

  async function fetchUserInfo() {
    const res = await getCurrentUser()
    userInfo.value = res.data
    permissions.value = res.data.permissions || []
    return res.data
  }

  async function fetchMenus() {
    const res = await getMenus()
    menus.value = res.data || []
    return res.data
  }

  function hasPerm(code: string) {
    if (permissions.value.includes('*')) return true
    return permissions.value.includes(code)
  }

  function setToken(t: string) {
    token.value = t
    persistToken(t)
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    menus.value = []
    permissions.value = []
    clearToken()
  }

  return { userInfo, token, menus, permissions, fetchUserInfo, fetchMenus, hasPerm, setToken, logout }
})
