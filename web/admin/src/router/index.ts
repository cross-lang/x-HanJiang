import { createRouter, createWebHistory } from 'vue-router'

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
      redirect: '/dashboard',
      children: [
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: () => import('@/views/dashboard/Dashboard.vue'),
        },
        {
          path: 'panel',
          name: 'DashboardPanel',
          component: () => import('@/views/dashboard/DashboardPanel.vue'),
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
          path: 'app-scopes',
          name: 'AppScopes',
          component: () => import('@/views/openapi/OpenScopeList.vue'),
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
      ],
    },
  ],
})

// 路由守卫：未登录跳登录页
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  if (to.path !== '/login' && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
