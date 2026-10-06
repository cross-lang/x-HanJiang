/** 开放平台门户账号体系类型（与 server 侧 developers 域约定对齐） */

/** 注册请求（所有字段均为必填） */
export interface RegisterRequest {
  username: string
  email: string
  password: string
  confirm_password: string
  /** 昵称（必填） */
  name: string
  /** 认证主体类型（必填）：personal / enterprise */
  certification_type: 'personal' | 'enterprise'
}

/** 登录请求 */
export interface LoginRequest {
  /** 用户名或邮箱 */
  account: string
  password: string
}

/** 登录结果（有状态会话：JWT + 服务端登录态，登出/改密后旧令牌即失效） */
export interface LoginResult {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

/** 修改密码请求 */
export interface ChangePasswordRequest {
  old_password: string
  new_password: string
  confirm_password: string
}

/** 忘记密码请求：提交注册邮箱，触发重置邮件 */
export interface ForgotPasswordRequest {
  email: string
}

/** 重置密码请求：邮件令牌 + 新密码 */
export interface ResetPasswordRequest {
  token: string
  new_password: string
  confirm_password: string
}

/** 开发者主体信息（预留字段：个人认证 / 企业认证） */
export interface DeveloperProfile {
  id: number
  username: string
  email: string
  name: string
  phone: string | null
  avatar_url: string | null
  /** 认证主体类型：personal 个人认证 / enterprise 企业认证 / null 未认证 */
  certification_type: 'personal' | 'enterprise' | null
  /** 企业名称（企业认证时填写） */
  company_name: string | null
  /** 认证状态：none / pending / approved / rejected */
  certification_status: 'none' | 'pending' | 'approved' | 'rejected'
  created_at: string
}

/** 更新开发者资料请求 */
export interface DeveloperUpdateRequest {
  name?: string
  phone?: string
  avatar_url?: string | null
}

/** 认证申请请求（预留：个人认证 / 企业认证） */
export interface CertificationRequest {
  certification_type: 'personal' | 'enterprise'
  company_name?: string
  /** 身份证号 / 统一社会信用代码（演示阶段可选填） */
  credential_no?: string
}
