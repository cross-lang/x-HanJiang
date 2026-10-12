// 时间格式化工具（src/utils/format.ts）行为测试
import { describe, it, expect } from 'vitest'
import { formatDateTime } from '@/utils/format'

describe('utils/format formatDateTime', () => {
  it('带 T 的时间戳统一格式化为 YYYY-MM-DD HH:mm:ss', () => {
    // 不带时区后缀 → 按本地时间解析，输出确定
    expect(formatDateTime('2026-10-03T12:00:00')).toBe('2026-10-03 12:00:00')
  })

  it('已是显示格式（无 T）的字符串保持原样，不二次补零', () => {
    expect(formatDateTime('2026-10-03 20:58:41')).toBe('2026-10-03 20:58:41')
  })

  it('空值（null / undefined / 空串）统一显示为 "-"', () => {
    expect(formatDateTime(null)).toBe('-')
    expect(formatDateTime(undefined)).toBe('-')
    expect(formatDateTime('')).toBe('-')
  })

  it('无法解析的非法字符串原样返回', () => {
    expect(formatDateTime('not-a-date')).toBe('not-a-date')
  })
})
