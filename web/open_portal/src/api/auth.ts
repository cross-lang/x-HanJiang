import request from './request'
import type {
  ChangePasswordRequest,
  ForgotPasswordRequest,
  LoginRequest,
  LoginResult,
  RegisterRequest,
  ResetPasswordRequest,
  UpdateEmailRequest,
  UpdatePhoneRequest,
} from '@/types/auth'

/**
 * 开放平台门户账号体系接口。
 * 开发者账号存 developers 表（与管理系统 users 分表）；
 * 鉴权为有状态会话（JWT + Redis 登录态），登出/修改密码后旧令牌即失效。
 */

/** 注册开发者账号 */
export function register(data: RegisterRequest) {
  return request.post<{ message: string }>('/auth/register', data)
}

/** 登录（用户名或邮箱 + 密码） */
export function login(data: LoginRequest) {
  return request.post<LoginResult>('/auth/login', data)
}

/** 刷新令牌（换取新令牌对，旧 access token 随之失效） */
export function refreshToken(refresh_token: string) {
  return request.post<LoginResult>('/auth/refresh', { refresh_token })
}

/** 退出登录（撤销服务端登录态） */
export function logout() {
  return request.post<{ message: string }>('/auth/logout')
}

/** 修改密码（成功后服务端登录态被撤销，需重新登录） */
export function changePassword(data: ChangePasswordRequest) {
  return request.post<{ message: string }>('/auth/change-password', data)
}

/** 发送邮箱验证码（修改手机号/邮箱前的二次认证） */
export function sendVerifyCode() {
  return request.post<{ message: string }>('/auth/send-verify-code')
}

/** 修改手机号（需邮箱验证码二次认证） */
export function updatePhone(data: UpdatePhoneRequest) {
  return request.post<{ message: string }>('/auth/update-phone', data)
}

/** 修改邮箱（需原邮箱验证码二次认证） */
export function updateEmail(data: UpdateEmailRequest) {
  return request.post<{ message: string }>('/auth/update-email', data)
}

/** 忘记密码：提交注册邮箱，向邮箱发送一次性重置链接（30 分钟有效） */
export function forgotPassword(data: ForgotPasswordRequest) {
  return request.post<{ message: string }>('/auth/forgot-password', data)
}

/** 重置密码：携带邮件令牌 + 新密码完成重置 */
export function resetPassword(data: ResetPasswordRequest) {
  return request.post<{ reset: boolean }>('/auth/reset-password', data)
}
