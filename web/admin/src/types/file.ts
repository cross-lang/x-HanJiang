/** 文件管理类型（与 server/src/services/file_service.py 返回结构对齐） */

export interface FileItem {
  id: number
  original_name: string
  extension: string
  mime_type: string
  size_bytes: number
  folder: string
  storage_type: string
  url: string
  uploaded_by: number | null
  uploader_name: string | null
  uploader_display: string | null
  is_public: boolean
  created_at: string | null
}

export interface StorageStats {
  total_size_bytes: number
  total_count: number
  by_folder: { folder: string; count: number; size_bytes: number }[]
}
