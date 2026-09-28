/**
 * 公告正文渲染工具
 * Markdown 经 marked 渲染、富文本直接使用，统一过 DOMPurify 消毒，防止 XSS。
 */
import { marked } from 'marked'
import DOMPurify from 'dompurify'

export function renderAnnouncement(content: string, contentType: string): string {
  const raw = contentType === 'richtext' ? content : (marked.parse(content, { async: false }) as string)
  return DOMPurify.sanitize(raw, { USE_PROFILES: { html: true } })
}
