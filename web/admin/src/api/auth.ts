import request from './request'
import type { LoginRequest, LoginResult, MenuItem, UserInfo } from '@/types/auth'

/** 登录（用户名或邮箱 + 密码） */
export function login(data: LoginRequest) {
  return request.post<LoginResult>('/auth/login', data)
}

/** 获取当前登录用户信息 */
export function getCurrentUser() {
  return request.get<UserInfo>('/profile/me')
}

/** 获取当前用户可见菜单树 */
export function getMenus() {
  return request.get<MenuItem[]>('/profile/menus')
}

/** 退出登录 */
export function logout() {
  return request.post<{ message: string }>('/auth/logout')
}
