import axios, { type AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import type { ApiResponse } from '@/types/api'
import { clearToken, getToken } from '@/utils/storage'

const http = axios.create({
  // 开放平台门户自身接口统一挂在 /api/open/v1 前缀下（与管理系统 /api/v1 域隔离）
  baseURL: '/api/open/v1',
  timeout: 10000,
})

// 请求拦截器：自动带登录态 token（JWT Bearer）
http.interceptors.request.use(config => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一处理错误；保留完整响应交由下方泛型方法解包
http.interceptors.response.use(
  response => response,
  error => {
    // 401：会话失效跳登录；未登录场景静默，不弹错误提示
    if (error.response?.status === 401) {
      if (!window.location.pathname.includes('/login')) {
        clearToken()
        window.location.href = '/login'
      }
      return Promise.reject(error)
    }
    const msg = error.response?.data?.message || '请求失败'
    ElMessage.error(msg)
    return Promise.reject(error)
  },
)

async function unwrap<T>(promise: Promise<{ data: ApiResponse<T> }>): Promise<ApiResponse<T>> {
  const response = await promise
  return response.data
}

/**
 * 泛型请求封装：get/post/put/patch/delete 均返回后端包裹体 ApiResponse<T>，
 * 调用方通过 res.data 取业务数据，类型随 T 收窄。
 */
export const request = {
  get: <T>(url: string, config?: AxiosRequestConfig) => unwrap<T>(http.get<ApiResponse<T>>(url, config)),
  post: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    unwrap<T>(http.post<ApiResponse<T>>(url, data, config)),
  put: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    unwrap<T>(http.put<ApiResponse<T>>(url, data, config)),
  patch: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    unwrap<T>(http.patch<ApiResponse<T>>(url, data, config)),
  delete: <T>(url: string, config?: AxiosRequestConfig) => unwrap<T>(http.delete<ApiResponse<T>>(url, config)),
}

export default request
