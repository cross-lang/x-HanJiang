import request from './request'
import type { DashboardStats, MyActivity, NotificationMonitor } from '@/types/dashboard'

/** 仪表盘核心统计 */
export function getDashboardStats() {
  return request.get<DashboardStats>('/dashboard/stats')
}

/** 首页：我的最近登录与操作 */
export function getMyActivity() {
  return request.get<MyActivity>('/dashboard/my-activity')
}

/** 系统监控：CPU/内存/磁盘/网络指标 */
export function getNotificationMonitor() {
  return request.get<NotificationMonitor>('/admin/system-monitor/system')
}
