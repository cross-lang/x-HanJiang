import request from './request'
import type { PageResult } from '@/types/api'
import type { FileItem, StorageStats } from '@/types/file'

export interface FileQuery {
  page: number
  page_size: number
  keyword?: string
  folder?: string
}

export function listFiles(params: FileQuery) {
  return request.get<PageResult<FileItem>>('/files', { params })
}

export function getStorageStats() {
  return request.get<StorageStats>('/files/stats')
}

export function uploadFile(formData: FormData) {
  return request.post<FileItem>('/files/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function deleteFile(id: number) {
  return request.delete<{ message: string }>(`/files/${id}`)
}

/** 下载文件（原始 fetch，返回 Blob，调用方负责落盘） */
export function downloadFileBlob(key: string): Promise<Response> {
  const token = localStorage.getItem('access_token')
  return fetch(`/api/v1/files/${key}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
}
