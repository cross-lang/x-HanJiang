import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getCurrentUser } from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  const userInfo = ref<any>(null)
  const token = ref(localStorage.getItem('access_token') || '')

  async function fetchUserInfo() {
    const res = await getCurrentUser()
    userInfo.value = res.data
    return res.data
  }

  function setToken(t: string) {
    token.value = t
    localStorage.setItem('access_token', t)
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('access_token')
  }

  return { userInfo, token, fetchUserInfo, setToken, logout }
})
