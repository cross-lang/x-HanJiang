import JSEncrypt from 'jsencrypt'

/** 登录公钥接口响应（GET /auth/public-key） */
export interface LoginPublicKey {
  public_key: string
  nonce: string
  timestamp: number
  expires_in: number
}

/**
 * 用 RSA-OAEP(SHA-256) 加密 `nonce|timestamp|password`，返回 base64 密文。
 * jsencrypt 的 encryptOAEP 固定使用 RSA_PKCS1_OAEP_PADDING + oaepHash sha256，
 * 与后端 pycryptodome `PKCS1_OAEP.new(key, hashAlgo=SHA256)` 完全兼容。
 * 纯 JS 实现，不依赖 Web Crypto 的安全上下文（http 内网 IP 下也可用）。
 */
export function encryptLoginPassword(password: string, pub: LoginPublicKey): string {
  const enc = new JSEncrypt({ default_key_size: '4096' })
  enc.setPublicKey(pub.public_key)
  const cipher = enc.encryptOAEP(`${pub.nonce}|${pub.timestamp}|${password}`)
  if (!cipher) {
    throw new Error('密码加密失败，请重试')
  }
  return cipher
}
