import request from './request'
import type { ChangePasswordRequest, LoginRequest, LoginResult, RegisterRequest } from '@/types/auth'

/**
 * 开放平台门户账号体系接口。
 * 注意：developers 域（开发者账号）为规划中的独立用户体系，以下接口当前处于
 * 「前端已接入、后端待实现」状态，接口路径为约定值，后端就绪后按此契约落地。
 */

/** 注册开发者账号 */
export function register(data: RegisterRequest) {
  return request.post<{ message: string }>('/auth/register', data)
}

/** 登录（用户名或邮箱 + 密码） */
export function login(data: LoginRequest) {
  return request.post<LoginResult>('/auth/login', data)
}

/** 退出登录 */
export function logout() {
  return request.post<{ message: string }>('/auth/logout')
}

/** 修改密码 */
export function changePassword(data: ChangePasswordRequest) {
  return request.post<{ message: string }>('/auth/change-password', data)
}
