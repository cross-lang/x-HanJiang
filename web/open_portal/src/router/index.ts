import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '@/utils/storage'
import { useDeveloperStore } from '@/stores/developer'
import { capabilityModuleMap } from '@/data/capability'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/login/Login.vue'),
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('@/views/register/Register.vue'),
    },
    {
      path: '/',
      component: () => import('@/views/layout/Layout.vue'),
      redirect: '/home',
      children: [
        { path: 'home', name: 'Home', component: () => import('@/views/home/Home.vue') },
        { path: 'apps', name: 'Apps', component: () => import('@/views/apps/Apps.vue') },
        {
          // 接口级详情页：开放能力 → 模块（二级）→ 具体接口（三级）
          path: 'capability/:module/:apiId',
          name: 'CapabilityApi',
          component: () => import('@/views/capability/CapabilityModule.vue'),
        },
        // 模块路径 → 该模块第一个接口（兼容旧书签/入口）
        {
          path: 'capability/:module',
          redirect: to => {
            const m = capabilityModuleMap[to.params.module as keyof typeof capabilityModuleMap]
            return `/capability/${to.params.module}/${m?.apis[0]?.id ?? 'health-check'}`
          },
        },
        // 兼容旧路径：原"开放接口"页（/docs → /api-docs）已被"开放能力"三级菜单页取代
        { path: 'api-docs', redirect: '/capability/user/user-create' },
        {
          path: 'auth',
          name: 'AuthGuide',
          redirect: '/auth/modes',
          children: [
            { path: 'modes', name: 'AuthModes', component: () => import('@/views/auth/AuthModes.vue') },
            { path: 'signature', name: 'SignatureAlgo', component: () => import('@/views/auth/SignatureAlgo.vue') },
            { path: 'params', name: 'CommonParams', component: () => import('@/views/auth/CommonParams.vue') },
            { path: 'errors', name: 'ErrorCodes', component: () => import('@/views/auth/ErrorCodes.vue') },
          ],
        },
        { path: 'profile', name: 'Profile', component: () => import('@/views/profile/Profile.vue') },
      ],
    },
  ],
})

// 无需登录即可访问的公共路径（登录/注册对外可见）
const PUBLIC_PATHS: ReadonlySet<string> = new Set(['/login', '/register'])

/**
 * 全局路由守卫：登录态校验。
 * 1. 未登录：仅放行公共路径，其余一律跳登录页；
 * 2. 已登录访问登录/注册页：回到首页。
 * （开放平台为独立门户，无管理系统那种基于权限码的菜单体系，仅需登录态即可进入。）
 */
router.beforeEach(async to => {
  if (!getToken()) {
    return PUBLIC_PATHS.has(to.path) ? true : '/login'
  }
  if (PUBLIC_PATHS.has(to.path)) {
    return '/home'
  }

  const store = useDeveloperStore()
  if (!store.profile) {
    try {
      await store.fetchProfile()
    } catch {
      store.logout()
      return '/login'
    }
  }
  return true
})

export default router
