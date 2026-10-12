// HanJiang-1 开放接口签名工具（src/utils/openSign.ts）行为测试。
// 用固定时间戳替代系统时间，保证摘要/签名结果完全确定；并以 node:crypto 作参照实现交叉校验。
import { describe, it, expect } from 'vitest'
import { createHash, createHmac } from 'node:crypto'
import {
  HANJIANG_ALGORITHM,
  HANJIANG_CONTENT_TYPE,
  buildSigningString,
  sha256Hex,
  hmacSha256Hex,
  buildSignedHeaders,
} from '@/utils/openSign'

// 固定时间戳（RFC1123 GMT），替代真实时钟，保证用例确定可复现
const FIXED_DATE = 'Sat, 03 Oct 2026 12:00:00 GMT'
const APP_KEY = 'your-app-key'
const APP_ID = 'hj_xxxxxxxx'

describe('openSign 签名串拼接（参与签名字段与顺序）', () => {
  it('GET 空 body：六段直接拼接无分隔符，body 摘要段为空', () => {
    const s = buildSigningString({ method: 'get', uri: '/api/open/v1/health', date: FIXED_DATE })
    // 注意：method 即使传入小写 get，内部也须转成大写 GET
    expect(s).toBe(
      [HANJIANG_ALGORITHM, 'GET', '/api/open/v1/health', HANJIANG_CONTENT_TYPE, FIXED_DATE, ''].join(''),
    )
    // 显式断言结尾不带 body 摘要（空 body 时为空串）
    expect(s.endsWith(FIXED_DATE)).toBe(true)
  })

  it('POST 带 body：拼接结果末尾追加 body 的 SHA256 十六进制摘要', () => {
    const body = '{"username":"demo","name":"演示"}'
    const s = buildSigningString({ method: 'POST', uri: '/api/open/v1/users', date: FIXED_DATE, body })
    const expectBodyHash = createHash('sha256').update(body, 'utf8').digest('hex')
    // 签名串 = 前缀各段 + body 摘要，且无分隔符
    expect(s).toBe(
      [HANJIANG_ALGORITHM, 'POST', '/api/open/v1/users', HANJIANG_CONTENT_TYPE, FIXED_DATE, expectBodyHash].join(''),
    )
  })
})

describe('openSign 摘要与 HMAC 结果格式', () => {
  it('sha256Hex 空 body 返回空串；非空为 64 位小写十六进制，与 node 参照一致', () => {
    expect(sha256Hex('')).toBe('')
    expect(sha256Hex(undefined)).toBe('')
    const body = 'hello'
    const h = sha256Hex(body)
    expect(h).toMatch(/^[0-9a-f]{64}$/)
    expect(h).toBe(createHash('sha256').update(body, 'utf8').digest('hex'))
  })

  it('hmacSha256Hex 输出 64 位小写十六进制，与 node crypto 参照一致，且确定性可复现', () => {
    const signingString = buildSigningString({ method: 'GET', uri: '/api/open/v1/health', date: FIXED_DATE })
    const sig = hmacSha256Hex(APP_KEY, signingString)
    const expected = createHmac('sha256', APP_KEY).update(signingString, 'utf8').digest('hex')
    expect(sig).toMatch(/^[0-9a-f]{64}$/)
    expect(sig).toBe(expected)
    // 同样输入再次计算结果一致（mock 固定时间戳后无随机性）
    expect(hmacSha256Hex(APP_KEY, signingString)).toBe(sig)
  })

  it('篡改请求体会改变签名（摘要参与签名，具备完整性）', () => {
    const a = hmacSha256Hex(APP_KEY, buildSigningString({ method: 'POST', uri: '/u', date: FIXED_DATE, body: '{"a":1}' }))
    const b = hmacSha256Hex(APP_KEY, buildSigningString({ method: 'POST', uri: '/u', date: FIXED_DATE, body: '{"a":2}' }))
    expect(a).not.toBe(b)
  })
})

describe('openSign buildSignedHeaders 请求头拼装', () => {
  it('产出 X-App-Id / X-App-Date / X-App-Authorization / Content-Type 四要素，格式正确', () => {
    const headers = buildSignedHeaders({
      appId: APP_ID,
      appKey: APP_KEY,
      method: 'GET',
      uri: '/api/open/v1/health',
      date: FIXED_DATE,
    })
    const expectSig = hmacSha256Hex(
      APP_KEY,
      buildSigningString({ method: 'GET', uri: '/api/open/v1/health', date: FIXED_DATE }),
    )
    expect(headers['X-App-Id']).toBe(APP_ID)
    // X-App-Date 必须与签名串中的 Date 完全同值
    expect(headers['X-App-Date']).toBe(FIXED_DATE)
    expect(headers['X-App-Authorization']).toBe(`${HANJIANG_ALGORITHM} ${APP_ID}:${expectSig}`)
    // Content-Type 固定 application/json，与是否带 body 无关
    expect(headers['Content-Type']).toBe(HANJIANG_CONTENT_TYPE)
  })
})
