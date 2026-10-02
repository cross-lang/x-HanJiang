/** 公告相关类型（与 server/src/schemas/announcement.py 对齐） */

export type AnnouncementContentType = 'markdown' | 'richtext'
export type AnnouncementPosition = 'board' | 'banner'
export type AnnouncementStatus = 'draft' | 'published' | 'unpublished'

export interface AnnouncementItem {
  id: number
  title: string
  content: string
  content_type: AnnouncementContentType
  position: AnnouncementPosition
  status: AnnouncementStatus
  start_at: string | null
  end_at: string | null
  sort_order: number
  operator_id: number | null
  operator_name: string | null
  published_at: string | null
  created_at: string | null
  updated_at: string | null
  is_expired: boolean
}

export interface AnnouncementFormPayload {
  title: string
  content: string
  content_type: AnnouncementContentType
  position: AnnouncementPosition
  start_at: string
  end_at: string
  sort_order: number
}
