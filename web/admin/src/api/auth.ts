import request from './request'

export function login(data: { username: string; password: string }) {
  return request.post('/auth/login', data)
}

export function getCurrentUser() {
  return request.get('/profile/me')
}

export function getMenus() {
  return request.get('/profile/menus')
}

export function logout() {
  return request.post('/auth/logout')
}
