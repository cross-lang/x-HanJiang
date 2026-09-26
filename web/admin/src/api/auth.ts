import request from './request'

export function login(data: { username: string; password: string }) {
  return request.post('/auth/login', data)
}

export function getCurrentUser() {
  return request.get('/auth/me')
}

export function logout() {
  return request.post('/auth/logout')
}
