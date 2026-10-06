import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '@/utils/storage'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/login/Login.vue'),
    },
    {
      path: '/',
      component: () => import('@/views/layout/Layout.vue'),
      redirect: '/home',
      children: [
        {
          path: 'home',
          name: 'Home',
          component: () => import('@/views/dashboard/Dashboard.vue'),
          meta: { perm: 'home:view' },
        },
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: () => import('@/views/dashboard/DashboardPanel.vue'),
          meta: { perm: 'dashboard:view' },
        },
        {
          path: 'users',
          name: 'Users',
          component: () => import('@/views/system/UserList.vue'),
        },
        {
          path: 'roles',
          name: 'Roles',
          component: () => import('@/views/system/RoleList.vue'),
        },
        {
          path: 'permissions',
          name: 'Permissions',
          component: () => import('@/views/system/PermissionList.vue'),
        },
        {
          path: 'apis/swagger',
          name: 'SwaggerDoc',
          component: () => import('@/views/docs/SwaggerDoc.vue'),
        },
        {
          path: 'audit',
          name: 'Audit',
          component: () => import('@/views/audit/AuditLog.vue'),
        },
        {
          path: 'audit/login',
          name: 'LoginLog',
          component: () => import('@/views/audit/AuditLog.vue'),
          props: { logType: 'login' },
        },
        {
          path: 'apps',
          name: 'Apps',
          component: () => import('@/views/openapi/OpenAppList.vue'),
        },
        {
          path: 'app-approvals',
          name: 'AppApprovals',
          component: () => import('@/views/openapi/AppApprovalList.vue'),
          meta: { perm: 'openapi_app:approve' },
        },
        {
          path: 'app-scopes',
          name: 'AppScopes',
          component: () => import('@/views/openapi/OpenScopeList.vue'),
        },
        {
          path: 'open-developers',
          name: 'OpenDevelopers',
          component: () => import('@/views/openapi/DeveloperList.vue'),
          meta: { perm: 'openapi_dev:view' },
        },
        {
          path: 'system-notification',
          name: 'SystemNotification',
          component: () => import('@/views/notification/SystemNotification.vue'),
        },
        {
          path: 'announcements',
          name: 'Announcements',
          component: () => import('@/views/announcement/AnnouncementList.vue'),
        },
        {
          path: 'profile',
          name: 'Profile',
          component: () => import('@/views/profile/Profile.vue'),
        },
        {
          path: 'files',
          name: 'Files',
          component: () => import('@/views/file/FileList.vue'),
        },
        {
          path: 'station-messages',
          name: 'StationMessages',
          component: () => import('@/views/station/StationMessages.vue'),
          meta: { perm: 'station:view' },
        },
      ],
    },
  ],
})

// 无需登录即可访问的公共路径
const PUBLIC_PATHS: ReadonlySet<string> = new Set(['/login'])
// 登录后无目标路由权限时的兜底落点（个人中心对所有登录用户默认可见）
const FALLBACK_PATH = '/profile'

/**
 * 全局路由守卫：登录态校验 + 按路由 meta.perm 做权限拦截。
 *
 * 校验顺序：
 * 1. 未登录：仅放行公共路径，其余一律跳登录页；
 * 2. 已登录访问登录页：回到首页；
 * 3. 权限尚未加载（刷新直达/首次进入）时，先拉取当前用户信息；
 * 4. 目标路由声明了 meta.perm 且当前用户无该权限：重定向到 FALLBACK_PATH。
 */
router.beforeEach(async to => {
  if (!getToken()) {
    return PUBLIC_PATHS.has(to.path) ? true : '/login'
  }
  if (to.path === '/login') {
    return '/'
  }

  const userStore = useUserStore()
  // 权限列表未加载时先获取用户信息，避免刷新/直达路由时误判
  if (!userStore.permissions.length) {
    try {
      await userStore.fetchUserInfo()
    } catch {
      // token 失效或网络异常：清除登录态并回到登录页
      userStore.logout()
      return '/login'
    }
  }

  const requiredPerm = to.meta.perm
  if (requiredPerm && !userStore.hasPerm(requiredPerm)) {
    return FALLBACK_PATH
  }
  return true
})

export default router
