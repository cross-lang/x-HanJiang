import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
    },
    {
      path: '/',
      component: () => import('@/views/Layout.vue'),
      redirect: '/dashboard',
      children: [
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: () => import('@/views/Dashboard.vue'),
        },
        {
          path: 'panel',
          name: 'DashboardPanel',
          component: () => import('@/views/DashboardPanel.vue'),
        },
        {
          path: 'users',
          name: 'Users',
          component: () => import('@/views/UserList.vue'),
        },
        {
          path: 'roles',
          name: 'Roles',
          component: () => import('@/views/RoleList.vue'),
        },
        {
          path: 'permissions',
          name: 'Permissions',
          component: () => import('@/views/PermissionList.vue'),
        },
        {
          path: 'apis/swagger',
          name: 'SwaggerDoc',
          component: () => import('@/views/SwaggerDoc.vue'),
        },
        {
          path: 'audit',
          name: 'Audit',
          component: () => import('@/views/AuditLog.vue'),
        },
        {
          path: 'apps',
          name: 'Apps',
          component: () => import('@/views/OpenAppList.vue'),
        },
        {
          path: 'profile',
          name: 'Profile',
          component: () => import('@/views/Profile.vue'),
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
