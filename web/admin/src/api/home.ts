import request from './request'
import type { MyActivity } from '@/types/home'

/** 首页：我的最近登录与操作记录 */
export function getMyActivity() {
  return request.get<MyActivity>('/home/my-activity')
}
