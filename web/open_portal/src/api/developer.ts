import request from './request'
import type { CertificationRequest, DeveloperProfile, DeveloperUpdateRequest } from '@/types/auth'

/**
 * 开发者资料与认证接口。
 * 现状：developers 域为规划中独立用户体系，以下接口前端已接入、后端待实现。
 */

/** 获取当前登录开发者资料 */
export function getDeveloperProfile() {
  return request.get<DeveloperProfile>('/developers/profile')
}

/** 更新开发者资料（姓名/手机/头像） */
export function updateDeveloperProfile(data: DeveloperUpdateRequest) {
  return request.put<DeveloperProfile>('/developers/profile', data)
}

/** 提交认证申请（个人认证 / 企业认证，预留） */
export function applyCertification(data: CertificationRequest) {
  return request.post<{ message: string }>('/developers/certification', data)
}
