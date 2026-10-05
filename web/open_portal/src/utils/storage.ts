/** 本地存储统一管理（键名收敛，避免散落各处） */

const TOKEN_KEY = 'open_access_token'
const REFRESH_TOKEN_KEY = 'open_refresh_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function setRefreshToken(token: string): void {
  localStorage.setItem(REFRESH_TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

export function getStorageJson<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : null
  } catch {
    return null
  }
}

export function setStorageJson(key: string, value: unknown): void {
  localStorage.setItem(key, JSON.stringify(value))
}

export function removeStorage(key: string): void {
  localStorage.removeItem(key)
}
