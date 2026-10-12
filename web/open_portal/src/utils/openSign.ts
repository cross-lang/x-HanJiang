/**
 * HanJiang-1 开放接口签名工具。
 *
 * 与「认证和授权 / 签名算法」文档页（src/views/auth/SignatureAlgo.vue）及
 * server/examples/openapi_client.py、Go 示例中的算法严格对齐：
 *
 *   签名串 = "HanJiang-1" + METHOD(大写) + URI + "application/json" + Date + SHA256Hex(body)
 *
 * 约定：各段直接拼接、无任何分隔符；GET 等空请求体时 body 摘要取空字符串；
 * Content-Type 固定为 application/json（与是否携带 body 无关）；
 * Date 为 RFC1123 GMT 格式，必须与请求头 X-App-Date 完全同值。
 *
 * 说明：本模块使用 node:crypto 做确定性摘要/hmac，仅供「签名示例」演示与测试验证，
 * 未被任何页面/路由引用，因此不进入生产构建图。
 */
import { createHash, createHmac } from 'node:crypto'

/** 算法名（签名串首段，也是 Authorization 头前缀） */
export const HANJIANG_ALGORITHM = 'HanJiang-1'
/** 固定 Content-Type，与是否携带请求体无关 */
export const HANJIANG_CONTENT_TYPE = 'application/json'

export interface BuildSigningStringInput {
  /** HTTP 方法，内部统一转大写 */
  method: string
  /** 含 /api/open/v1 前缀、不含域名的完整路径 + 查询串 */
  uri: string
  /** RFC1123 GMT 时间，须与 X-App-Date 请求头同值 */
  date: string
  /** 请求体；无 body 传空串 / 空 Uint8Array / undefined */
  body?: Uint8Array | string
}

/** 将入参请求体归一为 UTF-8 字节 */
function toBytes(body: Uint8Array | string | undefined): Uint8Array {
  if (!body) return new Uint8Array()
  if (typeof body === 'string') return new TextEncoder().encode(body)
  return body
}

/**
 * body 的 SHA256 十六进制小写摘要。
 * 空 body 时返回空字符串（与文档「GET 无请求体取空字符串」一致）。
 */
export function sha256Hex(body: Uint8Array | string | undefined): string {
  const bytes = toBytes(body)
  if (bytes.length === 0) return ''
  return createHash('sha256').update(bytes).digest('hex')
}

/** 拼接待签名串（六段直接拼接，无分隔符） */
export function buildSigningString(input: BuildSigningStringInput): string {
  const bodyHash = sha256Hex(input.body)
  return [
    HANJIANG_ALGORITHM,
    input.method.toUpperCase(),
    input.uri,
    HANJIANG_CONTENT_TYPE,
    input.date,
    bodyHash,
  ].join('')
}

/** 以 AppKey 为密钥计算 HMAC-SHA256，输出十六进制小写（64 位） */
export function hmacSha256Hex(appKey: string, signingString: string): string {
  return createHmac('sha256', appKey).update(signingString, 'utf8').digest('hex')
}

/** 签名后需携带的请求头集合 */
export interface SignedHeaders {
  'X-App-Id': string
  'X-App-Date': string
  /** 形如：HanJiang-1 hj_xxxxxxxx:<signature> */
  'X-App-Authorization': string
  'Content-Type': string
}

export interface BuildSignedHeadersOptions {
  appId: string
  appKey: string
  method: string
  uri: string
  date: string
  body?: Uint8Array | string
}

/** 一次性产出签名所需的全部请求头 */
export function buildSignedHeaders(opts: BuildSignedHeadersOptions): SignedHeaders {
  const signingString = buildSigningString(opts)
  const signature = hmacSha256Hex(opts.appKey, signingString)
  return {
    'X-App-Id': opts.appId,
    'X-App-Date': opts.date,
    'X-App-Authorization': `${HANJIANG_ALGORITHM} ${opts.appId}:${signature}`,
    'Content-Type': HANJIANG_CONTENT_TYPE,
  }
}
