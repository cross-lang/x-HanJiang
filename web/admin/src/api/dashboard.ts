import request from './request'
import type { DashboardStats, NotificationMonitor } from '@/types/dashboard'

/** 仪表盘核心统计 */
export function getDashboardStats() {
  return request.get<DashboardStats>('/dashboard/stats')
}

/** 系统监控：CPU/内存/磁盘/网络指标 */
export function getNotificationMonitor() {
  return request.get<NotificationMonitor>('/system-monitor/system')
}
