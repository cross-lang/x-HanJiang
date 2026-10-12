/**
 * 审计日志"编码 → 中文描述"格式化测试。
 * 命中映射输出 "code（中文）"，未命中原样返回（保证后端新增枚举无需改前端）。
 */
import { describe, expect, it } from 'vitest'
import { formatAuditEntity, formatAuditAction } from '../audit-labels'

describe('formatAuditEntity 实体编码', () => {
  it('命中实体编码时输出 "编码（中文）"', () => {
    expect(formatAuditEntity('user')).toBe('user（用户）')
    expect(formatAuditEntity('openapi_app')).toBe('openapi_app（开放应用）')
  })

  it('未命中的实体编码原样返回，不补括号', () => {
    expect(formatAuditEntity('brand_new_entity')).toBe('brand_new_entity')
  })
})

describe('formatAuditAction 操作编码', () => {
  it('命中动作编码时输出 "编码（中文）"', () => {
    expect(formatAuditAction('create')).toBe('create（创建）')
    expect(formatAuditAction('rotate_key')).toBe('rotate_key（重置密钥）')
  })

  it('登录/登出动作有中文映射', () => {
    expect(formatAuditAction('login')).toBe('login（登录）')
    expect(formatAuditAction('logout')).toBe('logout（退出登录）')
  })

  it('未命中的动作编码原样返回', () => {
    expect(formatAuditAction('mystery')).toBe('mystery')
  })
})
