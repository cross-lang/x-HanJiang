import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    /**
     * 访问该路由所需的权限标识（如 `home:view`）。
     * 缺省表示仅需登录即可访问。
     */
    perm?: string
  }
}
