/**
 * 通用时间格式化：把 ISO 字符串（2026-09-27T20:58:41.123456+00:00）
 * 转为大众易读格式（2026-09-27 20:58:41）。
 * 已格式化的字符串或无法解析的值原样返回，空值显示 "-"。
 */
export function formatDateTime(value: unknown): string {
  if (value === null || value === undefined || value === '') return '-'
  const s = String(value)
  if (s.includes('T')) {
    return s.replace('T', ' ').substring(0, 19)
  }
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) {
    return s.substring(0, 19)
  }
  return s
}
