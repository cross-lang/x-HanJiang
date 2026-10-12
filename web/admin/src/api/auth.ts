import request from './request'
import type { LoginPublicKey, LoginRequest, LoginResult, MenuItem, UserInfo } from '@/types/auth'

/** 获取登录公钥与一次性 nonce（登录前调用，用于 RSA 加密密码） */
export function getLoginPublicKey() {
  return request.get<LoginPublicKey>('/auth/public-key')
}

/** 登录（用户名/手机号/邮箱 + RSA 加密密码） */
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
