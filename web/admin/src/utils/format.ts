/**
 * 通用时间格式化（基于 dayjs，统一时区口径）。
 * 后端返回的 ISO 时间戳（含 +00:00 / Z）统一按本地时区渲染；
 * 已是显示格式（YYYY-MM-DD ...）的字符串保持原样，无法解析的值原样返回，空值显示 "-"。
 */
import dayjs from 'dayjs'

const DATETIME_FORMAT = 'YYYY-MM-DD HH:mm:ss'
const SHORT_FORMAT = 'YYYY-MM-DD HH:mm'
const MONTH_DAY_FORMAT = 'MM-DD HH:mm'

function parse(value: unknown): dayjs.Dayjs | null {
  if (value === null || value === undefined || value === '') return null
  const d = dayjs(String(value))
  return d.isValid() ? d : null
}

/** 2026-09-27 20:58:41（本地时区） */
export function formatDateTime(value: unknown): string {
  const d = parse(value)
  if (d === null) return value === null || value === undefined || value === '' ? '-' : String(value)
  const s = String(value)
  // 非 ISO 时间戳（已格式化字符串）保持原样，避免二次补零
  if (!s.includes('T') && /^\d{4}-\d{2}-\d{2}/.test(s)) return s
  return d.format(DATETIME_FORMAT)
}

/** 2026-09-27 20:58（本地时区，用于列表紧凑展示） */
export function formatDateTimeShort(value: unknown): string {
  const d = parse(value)
  if (d === null) return ''
  return d.format(SHORT_FORMAT)
}

/** 09-27 20:58（本地时区，用于会话/最近动态等省略年份的场景） */
export function formatMonthDayTime(value: unknown): string {
  const d = parse(value)
  if (d === null) return ''
  return d.format(MONTH_DAY_FORMAT)
}
