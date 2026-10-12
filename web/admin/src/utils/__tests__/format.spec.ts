/**
 * formatDateTime / formatDateTimeShort / formatMonthDayTime 行为测试。
 * 重点覆盖：空值兜底、已格式化字符串原样返回、非法值原样返回、ISO 时间戳格式化。
 * 断言尽量与时区解耦（ISO 分支只校验格式骨架），避免在不同 TZ 机器上波动。
 */
import { describe, expect, it } from 'vitest'
import { formatDateTime, formatDateTimeShort, formatMonthDayTime } from '../format'

describe('formatDateTime 通用时间格式化', () => {
  it('空值（null / undefined / 空串）统一显示为 "-"', () => {
    expect(formatDateTime(null)).toBe('-')
    expect(formatDateTime(undefined)).toBe('-')
    expect(formatDateTime('')).toBe('-')
  })

  it('已是 "YYYY-MM-DD HH:mm:ss" 的字符串保持原样，不二次补零', () => {
    // 不含 T 且匹配日期前缀 → 直接返回原文
    expect(formatDateTime('2026-09-27 20:58:41')).toBe('2026-09-27 20:58:41')
  })

  it('无法解析的非法字符串原样返回', () => {
    expect(formatDateTime('not-a-date')).toBe('not-a-date')
  })

  it('ISO 时间戳（带 T）被格式化为 "YYYY-MM-DD HH:mm:ss" 骨架', () => {
    const out = formatDateTime('2026-09-27T12:00:00Z')
    // 只校验格式骨架，具体时分由本地时区决定，不在此硬编码
    expect(out).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/)
  })
})

describe('formatDateTimeShort 紧凑展示', () => {
  it('合法时间输出 "YYYY-MM-DD HH:mm"', () => {
    expect(formatDateTimeShort('2026-09-27 20:58:41')).toBe('2026-09-27 20:58')
  })

  it('空值返回空串（列表占位由调用方处理）', () => {
    expect(formatDateTimeShort(null)).toBe('')
    expect(formatDateTimeShort('')).toBe('')
  })
})

describe('formatMonthDayTime 省略年份', () => {
  it('输出 "MM-DD HH:mm"', () => {
    expect(formatMonthDayTime('2026-09-27 20:58:41')).toBe('09-27 20:58')
  })

  it('非法值返回空串', () => {
    expect(formatMonthDayTime('oops')).toBe('')
  })
})
