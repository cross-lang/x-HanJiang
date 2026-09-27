import request from './request'

export function login(data: { username: string; password: string }) {
  return request.post('/auth/login', data)
}

export function getCurrentUser() {
  return request.get('/auth/me')
}

export function getMenus() {
  return request.get('/auth/menus')
}

export function logout() {
  return request.post('/auth/logout')
}
