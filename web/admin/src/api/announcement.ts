import request from './request'
import type { PageResult } from '@/types/api'
import type { AnnouncementItem, AnnouncementFormPayload } from '@/types/announcement'

export interface AnnouncementQuery {
  page: number
  page_size: number
  keyword?: string
  status?: string
  position?: string
}

export function listAnnouncements(params: AnnouncementQuery) {
  return request.get<PageResult<AnnouncementItem>>('/announcements/', { params })
}

export function getAnnouncement(id: number) {
  return request.get<AnnouncementItem>(`/announcements/${id}`)
}

export function createAnnouncement(data: AnnouncementFormPayload) {
  return request.post<AnnouncementItem>('/announcements/', data)
}

export function updateAnnouncement(id: number, data: Partial<AnnouncementFormPayload>) {
  return request.post<AnnouncementItem>(`/announcements/${id}/update`, data)
}

export function publishAnnouncement(id: number) {
  return request.post<{ message: string }>(`/announcements/${id}/publish`)
}

export function unpublishAnnouncement(id: number) {
  return request.post<{ message: string }>(`/announcements/${id}/unpublish`)
}

export function deleteAnnouncement(id: number) {
  return request.post<{ message: string }>(`/announcements/${id}/delete`)
}

/** 首页可用公告（进行中的 board/banner） */
export function listAvailableAnnouncements() {
  return request.get<PageResult<AnnouncementItem>>('/announcements/available')
}
