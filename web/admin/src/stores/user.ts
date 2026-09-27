import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getCurrentUser, getMenus } from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  const userInfo = ref<any>(null)
  const token = ref(localStorage.getItem('access_token') || '')
  const menus = ref<any[]>([])
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
    localStorage.setItem('access_token', t)
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    menus.value = []
    permissions.value = []
    localStorage.removeItem('access_token')
  }

  return { userInfo, token, menus, permissions, fetchUserInfo, fetchMenus, hasPerm, setToken, logout }
})
