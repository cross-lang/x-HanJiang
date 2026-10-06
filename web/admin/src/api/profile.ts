import request from './request'
import type { UserInfo } from '@/types/auth'

/** 通知偏好事件（/profile/notification-preferences 返回 events） */
export interface PreferenceEvent {
  event: string
  name: string
  channels: { code: string; enabled: boolean }[]
}

/** 通知接收人（存储于用户通知渠道配置的 JSON 数组，无独立主键，以 channel+recipient 定位） */
export interface NotificationRecipient {
  channel: string
  recipient: string
  label: string | null
  enabled: boolean
}

/** 更新当前用户基本信息 */
export function updateMe(data: Partial<Pick<UserInfo, 'name' | 'email' | 'phone' | 'gender' | 'birthday'>>) {
  return request.put<UserInfo>('/profile/me', data)
}

/** 修改密码（需验证码） */
export function changePassword(oldPassword: string, newPassword: string, code: string) {
  return request.post<{ message: string }>('/profile/change-password', {
    old_password: oldPassword,
    new_password: newPassword,
    code,
  })
}

/** 发送短信/邮件验证码 */
export function sendVerifyCode() {
  return request.post<{ message: string }>('/profile/send-verify-code')
}

/** 更新手机号（需验证码） */
export function updatePhone(phone: string, code: string) {
  return request.post<{ message: string }>('/profile/update-phone', { phone, code })
}

/** 更新邮箱（需验证码） */
export function updateEmail(email: string, code: string) {
  return request.post<{ message: string }>('/profile/update-email', { email, code })
}

/** 查询通知偏好 */
export function getNotificationPreferences() {
  return request.get<{ events: PreferenceEvent[] }>('/profile/notification-preferences')
}

/** 更新通知偏好（{ 事件: { 渠道: 是否启用 } }） */
export function updateNotificationPreferences(prefs: Record<string, Record<string, boolean>>) {
  return request.put<{ message: string }>('/profile/notification-preferences', prefs)
}

/** 查询通知接收人 */
export function listNotificationRecipients() {
  return request.get<{ items: NotificationRecipient[] }>('/profile/notification-recipients')
}

/** 新增通知接收人（同渠道同接收人重复添加时幂等更新） */
export function addNotificationRecipient(data: {
  channel: string
  recipient: string
  label?: string
  enabled?: boolean
}) {
  return request.post<{ updated: boolean }>('/profile/notification-recipients', data)
}

/** 更新通知接收人（channel+recipient 定位，label/enabled 可更新） */
export function updateNotificationRecipient(data: {
  channel: string
  recipient: string
  label?: string
  enabled?: boolean
}) {
  return request.put<{ updated: boolean }>('/profile/notification-recipients', data)
}

/** 删除通知接收人（channel+recipient 定位） */
export function removeNotificationRecipient(channel: string, recipient: string) {
  return request.delete<{ deleted: boolean }>('/profile/notification-recipients', {
    params: { channel, recipient },
  })
}
