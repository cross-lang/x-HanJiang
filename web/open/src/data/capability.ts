import type { CapabilityModule } from '@/types/capability'

/**
 * 开放能力接口目录（与 server/src/api/open/v1 真实实现一一对应）。
 * 仅展示与"认证和授权"文档一致的 hmac（HanJiang-1）签名模式；
 * plain 明文模式仅作调试备选，见各模块注意事项。
 */

/** 公共请求头（hmac 签名模式） */
const COMMON_HEADERS = [
  {
    name: 'Content-Type',
    type: 'string',
    required: true,
    values: 'application/json',
    limit: '固定为【application/json】',
    example: 'application/json',
    desc: '内容类型，固定为 JSON 格式（参与签名计算，GET 无 body 也需携带）',
  },
  {
    name: 'X-App-Id',
    type: 'string',
    required: true,
    values: '-',
    limit: '-',
    example: 'hj_xxxxxxxx',
    desc: '应用 ID（AppId），创建应用时生成',
  },
  {
    name: 'X-App-Date',
    type: 'string',
    required: true,
    values: '-',
    limit: '必须符合 RFC1123 规范',
    example: 'Sat, 03 Oct 2026 12:00:00 GMT',
    desc: '请求时间，用于签名与防重放（时间窗 300 秒）',
  },
  {
    name: 'X-App-Authorization',
    type: 'string',
    required: true,
    values: '-',
    limit: '-',
    example: 'HanJiang-1 hj_xxxxxxxx:{signature}',
    desc: 'HanJiang-1 签名值，详见「认证和授权 → 签名说明」',
  },
]

/** 响应体公共字段 */
const COMMON_RESPONSE_FIELDS = [
  { name: 'code', type: 'integer', required: true, values: '-', limit: '-', example: '200', desc: 'HTTP 状态码（与 HTTP 状态一致），200 成功 / 201 创建成功' },
  { name: 'message', type: 'string', required: true, values: '-', limit: '-', example: 'OK', desc: '提示信息，成功为 OK，失败为错误原因' },
  { name: 'data', type: 'object', required: true, values: '-', limit: '-', example: '{...}', desc: '业务数据，结构见各接口说明' },
  { name: 'timestamp', type: 'string', required: true, values: '-', limit: '-', example: '2026-10-03T12:00:00Z', desc: '响应时间（ISO8601 UTC）' },
  { name: 'request_id', type: 'string', required: true, values: '-', limit: '-', example: 'req_open_xxxxx', desc: '请求追踪 ID，排查问题时提供给管理员' },
]

/** cURL 前缀（本地联调默认地址） */
const BASE = 'http://127.0.0.1:8000/api/open/v1'

export const capabilityModules: CapabilityModule[] = [
  // ─────────────────────────── 健康管理 ───────────────────────────
  {
    key: 'health',
    name: '健康管理',
    desc: '轻量探活与版本信息，无需特定 scope，仅需有效应用凭证。',
    apis: [
      {
        id: 'health-check',
        name: '开放平台健康检查',
        method: 'GET',
        path: '/health',
        scope: '仅需有效应用凭证',
        summary: '轻量探活，确认开放平台网关正常且调用方凭证有效。',
        notes: [
          '无需申请 scope：任何审批通过的有效应用均可调用。',
          '凭证无效（AppId 不存在 / 停用 / 签名失败）返回 401。',
        ],
        limits: ['无。'],
        headers: COMMON_HEADERS,
        query: [],
        pathParams: [],
        body: [],
        curl: `curl -X GET "${BASE}/health" \\
  -H "X-App-Id: hj_xxxxxxxx" \\
  -H "X-App-Date: Sat, 03 Oct 2026 12:00:00 GMT" \\
  -H "X-App-Authorization: HanJiang-1 hj_xxxxxxxx:{signature}" \\
  -H "Content-Type: application/json"`,
        responseFields: [
          ...COMMON_RESPONSE_FIELDS,
          { name: 'data.status', type: 'string', required: false, values: 'ok', limit: '-', example: 'ok', desc: '健康状态' },
          { name: 'data.service', type: 'string', required: false, values: 'openapi', limit: '-', example: 'openapi', desc: '服务标识' },
          { name: 'data.app', type: 'string', required: false, values: '-', limit: '-', example: 'hanjiang', desc: '平台名称' },
        ],
        responseExample: JSON.stringify(
          {
            code: 200,
            message: 'OK',
            data: { status: 'ok', service: 'openapi', app: 'hanjiang' },
            timestamp: '2026-10-03T12:00:00Z',
            request_id: 'req_open_xxxxx',
          },
          null,
          2,
        ),
        responseDesc: '凭证有效时返回 ok 状态与服务标识。',
      },
      {
        id: 'version',
        name: '开放平台版本信息',
        method: 'GET',
        path: '/version',
        scope: '仅需有效应用凭证',
        summary: '返回开放平台 API 版本号。',
        notes: ['无需申请 scope。'],
        limits: ['无。'],
        headers: COMMON_HEADERS,
        query: [],
        pathParams: [],
        body: [],
        curl: `curl -X GET "${BASE}/version" \\
  -H "X-App-Id: hj_xxxxxxxx" \\
  -H "X-App-Date: Sat, 03 Oct 2026 12:00:00 GMT" \\
  -H "X-App-Authorization: HanJiang-1 hj_xxxxxxxx:{signature}" \\
  -H "Content-Type: application/json"`,
        responseFields: [
          ...COMMON_RESPONSE_FIELDS,
          { name: 'data.app_version', type: 'string', required: false, values: '-', limit: '-', example: '0.1.0', desc: '应用版本号' },
          { name: 'data.api_version', type: 'string', required: false, values: 'v1', limit: '-', example: 'v1', desc: '开放接口 API 版本' },
        ],
        responseExample: JSON.stringify(
          {
            code: 200,
            message: 'OK',
            data: { app_version: '0.1.0', api_version: 'v1' },
            timestamp: '2026-10-03T12:00:00Z',
            request_id: 'req_open_xxxxx',
          },
          null,
          2,
        ),
        responseDesc: '应用版本与开放接口 API 版本。',
      },
    ],
  },

  // ─────────────────────────── 应用信息 ───────────────────────────
  {
    key: 'app',
    name: '应用信息',
    desc: '当前调用方应用的身份信息，无需特定 scope。',
    apis: [
      {
        id: 'me',
        name: '当前开放平台应用信息',
        method: 'GET',
        path: '/me',
        scope: '仅需有效应用凭证',
        summary: '返回当前调用方应用信息（App ID、名称、鉴权模式、已授权 scope 等）。',
        notes: [
          '无需申请 scope：任何有效应用都能查询自己的信息。',
          'AppKey 明文不会在此返回，仅返回 App ID 等元信息。',
        ],
        limits: ['无。'],
        headers: COMMON_HEADERS,
        query: [],
        pathParams: [],
        body: [],
        curl: `curl -X GET "${BASE}/me" \\
  -H "X-App-Id: hj_xxxxxxxx" \\
  -H "X-App-Date: Sat, 03 Oct 2026 12:00:00 GMT" \\
  -H "X-App-Authorization: HanJiang-1 hj_xxxxxxxx:{signature}" \\
  -H "Content-Type: application/json"`,
        responseFields: [
          ...COMMON_RESPONSE_FIELDS,
          { name: 'data.app_id', type: 'string', required: false, values: '-', limit: '-', example: 'hj_530853d017a013b35a76', desc: '应用 ID' },
          { name: 'data.name', type: 'string', required: false, values: '-', limit: '-', example: '我的应用', desc: '应用名称' },
          { name: 'data.description', type: 'string', required: false, values: '-', limit: '-', example: '用于业务对接', desc: '应用描述' },
          { name: 'data.scopes', type: 'array[string]', required: false, values: 'user:read 等', limit: '已审批通过的 scope', example: '["user:read"]', desc: '已授权 scope 列表' },
          { name: 'data.auth_mode', type: 'string', required: false, values: 'plain / hmac / both', limit: '-', example: 'hmac', desc: '应用鉴权模式' },
          { name: 'data.rate_limit_per_minute', type: 'integer', required: false, values: '-', limit: '-', example: '600', desc: '每分钟调用限额（预留）' },
        ],
        responseExample: JSON.stringify(
          {
            code: 200,
            message: 'OK',
            data: {
              app_id: 'hj_530853d017a013b35a76',
              name: '我的应用',
              description: '用于业务对接',
              scopes: ['user:read', 'role:read'],
              auth_mode: 'hmac',
              rate_limit_per_minute: 600,
            },
            timestamp: '2026-10-03T12:00:00Z',
            request_id: 'req_open_xxxxx',
          },
          null,
          2,
        ),
        responseDesc: '当前调用方应用详情（AppKey 明文不会返回）。',
      },
    ],
  },

  // ─────────────────────────── 用户管理 ───────────────────────────
  {
    key: 'user',
    name: '用户管理',
    desc: '用户核心数据的开放能力（需 user:read / user:write scope）。',
    apis: [
      {
        id: 'user-create',
        name: '创建用户',
        method: 'POST',
        path: '/users',
        scope: 'user:write',
        summary: '创建用户（校验邮箱 / 用户名全局唯一）。',
        notes: [
          '用户名 / 邮箱全局唯一，重复返回 409。',
          'operator 上下文记录为调用方应用（App ID），而非终端用户。',
        ],
        limits: ['username 3-50 位；password 8-64 位；role_ids 至少 1 个。'],
        headers: COMMON_HEADERS,
        query: [],
        pathParams: [],
        body: [
          { name: 'username', type: 'string', required: true, values: '-', limit: '3-50 位', example: 'dev_user', desc: '用户名（全局唯一）' },
          { name: 'email', type: 'string', required: true, values: '-', limit: '邮箱格式', example: 'dev@example.com', desc: '邮箱（全局唯一）' },
          { name: 'password', type: 'string', required: true, values: '-', limit: '8-64 位', example: '********', desc: '初始密码' },
          { name: 'name', type: 'string', required: true, values: '-', limit: '-', example: '开发者', desc: '姓名' },
          { name: 'phone', type: 'string', required: true, values: '-', limit: '-', example: '13800000000', desc: '手机号' },
          { name: 'gender', type: 'string', required: true, values: 'male / female', limit: '-', example: 'male', desc: '性别' },
          { name: 'birthday', type: 'string', required: true, values: '-', limit: 'YYYY-MM-DD', example: '1990-01-01', desc: '生日' },
          { name: 'role_ids', type: 'array[number]', required: true, values: '-', limit: '至少 1 个', example: '[3]', desc: '角色 ID 列表' },
          { name: 'status', type: 'string', required: false, values: 'enabled / disabled', limit: '-', example: 'enabled', desc: '状态（默认 enabled）' },
        ],
        curl: `curl -X POST "${BASE}/users" \\
  -H "X-App-Id: hj_xxxxxxxx" \\
  -H "X-App-Date: Sat, 03 Oct 2026 12:00:00 GMT" \\
  -H "X-App-Authorization: HanJiang-1 hj_xxxxxxxx:{signature}" \\
  -H "Content-Type: application/json" \\
  -d '{"username":"dev_user","email":"dev@example.com","password":"********","name":"开发者","phone":"13800000000","gender":"male","birthday":"1990-01-01","role_ids":[3]}'`,
        responseFields: [
          ...COMMON_RESPONSE_FIELDS,
          { name: 'data.id', type: 'integer', required: false, values: '-', limit: '-', example: '3', desc: '用户 ID' },
          { name: 'data.username', type: 'string', required: false, values: '-', limit: '-', example: 'dev_user', desc: '用户名' },
          { name: 'data.email', type: 'string', required: false, values: '-', limit: '-', example: 'dev@example.com', desc: '邮箱' },
          { name: 'data.roles', type: 'array[object]', required: false, values: '-', limit: '-', example: '[{id,role_name,role_code}]', desc: '角色列表（不含密码哈希）' },
          { name: 'data.status', type: 'string', required: false, values: 'enabled / disabled', limit: '-', example: 'enabled', desc: '用户状态' },
        ],
        responseExample: JSON.stringify(
          {
            code: 201,
            message: 'OK',
            data: {
              id: 3,
              username: 'dev_user',
              email: 'dev@example.com',
              name: '开发者',
              roles: [{ id: 3, role_name: '普通用户', role_code: 'user' }],
              status: 'enabled',
            },
            timestamp: '2026-10-03T12:00:00Z',
            request_id: 'req_open_xxxxx',
          },
          null,
          2,
        ),
        responseDesc: '创建成功的用户信息（不含密码哈希）。',
      },
      {
        id: 'user-list',
        name: '用户列表',
        method: 'GET',
        path: '/users',
        scope: 'user:read',
        summary: '分页查询用户列表，支持关键字 / 状态过滤。',
        notes: ['page_size 最大 100。'],
        limits: ['keyword 按用户名 / 邮箱 / 姓名模糊搜索。'],
        headers: COMMON_HEADERS,
        query: [
          { name: 'page', type: 'number', required: false, values: '-', limit: '从 1 开始', example: '1', desc: '页码（默认 1）' },
          { name: 'page_size', type: 'number', required: false, values: '-', limit: '1-100，默认 20', example: '20', desc: '每页条数' },
          { name: 'keyword', type: 'string', required: false, values: '-', limit: '-', example: 'dev', desc: '用户名 / 邮箱 / 姓名模糊搜索' },
          { name: 'status', type: 'string', required: false, values: 'enabled / disabled', limit: '-', example: 'enabled', desc: '状态过滤' },
        ],
        pathParams: [],
        body: [],
        curl: `curl -X GET "${BASE}/users?page=1&page_size=20" \\
  -H "X-App-Id: hj_xxxxxxxx" \\
  -H "X-App-Date: Sat, 03 Oct 2026 12:00:00 GMT" \\
  -H "X-App-Authorization: HanJiang-1 hj_xxxxxxxx:{signature}" \\
  -H "Content-Type: application/json"`,
        responseFields: [
          ...COMMON_RESPONSE_FIELDS,
          { name: 'data.items', type: 'array[object]', required: false, values: '-', limit: '-', example: '[{id,username,name,roles,status}]', desc: '用户列表（不含密码哈希）' },
          { name: 'data.total', type: 'integer', required: false, values: '-', limit: '-', example: '1', desc: '总记录数' },
          { name: 'data.page', type: 'integer', required: false, values: '-', limit: '-', example: '1', desc: '当前页码' },
          { name: 'data.page_size', type: 'integer', required: false, values: '-', limit: '-', example: '20', desc: '每页条数' },
          { name: 'data.total_pages', type: 'integer', required: false, values: '-', limit: '-', example: '1', desc: '总页数' },
        ],
        responseExample: JSON.stringify(
          {
            code: 200,
            message: 'OK',
            data: {
              items: [{ id: 1, username: 'superadmin', name: '超级管理员', roles: [], status: 'enabled' }],
              total: 1,
              page: 1,
              page_size: 20,
              total_pages: 1,
            },
            timestamp: '2026-10-03T12:00:00Z',
            request_id: 'req_open_xxxxx',
          },
          null,
          2,
        ),
        responseDesc: '分页结构 {items, total, page, page_size, total_pages}。',
      },
      {
        id: 'user-get',
        name: '用户详情',
        method: 'GET',
        path: '/users/{user_id}',
        scope: 'user:read',
        summary: '查询单个用户详情。',
        notes: ['用户不存在返回 404（用户 {id} 不存在）。'],
        limits: ['无。'],
        headers: COMMON_HEADERS,
        query: [],
        pathParams: [{ name: 'user_id', type: 'number', required: true, values: '-', limit: '-', example: '2', desc: '用户 ID' }],
        body: [],
        curl: `curl -X GET "${BASE}/users/2" \\
  -H "X-App-Id: hj_xxxxxxxx" \\
  -H "X-App-Date: Sat, 03 Oct 2026 12:00:00 GMT" \\
  -H "X-App-Authorization: HanJiang-1 hj_xxxxxxxx:{signature}" \\
  -H "Content-Type: application/json"`,
        responseFields: [
          ...COMMON_RESPONSE_FIELDS,
          { name: 'data.id', type: 'integer', required: false, values: '-', limit: '-', example: '2', desc: '用户 ID' },
          { name: 'data.username', type: 'string', required: false, values: '-', limit: '-', example: 'yangzhuang', desc: '用户名' },
          { name: 'data.name', type: 'string', required: false, values: '-', limit: '-', example: '杨壮', desc: '姓名' },
          { name: 'data.status', type: 'string', required: false, values: 'enabled / disabled', limit: '-', example: 'enabled', desc: '用户状态' },
        ],
        responseExample: JSON.stringify(
          {
            code: 200,
            message: 'OK',
            data: { id: 2, username: 'yangzhuang', name: '杨壮', status: 'enabled' },
            timestamp: '2026-10-03T12:00:00Z',
            request_id: 'req_open_xxxxx',
          },
          null,
          2,
        ),
        responseDesc: '用户详情；不存在时返回 404。',
      },
      {
        id: 'user-update',
        name: '更新用户',
        method: 'PATCH',
        path: '/users/{user_id}',
        scope: 'user:write',
        summary: '更新用户信息（仅更新提供的字段）。',
        notes: ['字段全可选，仅更新传入字段。'],
        limits: ['无。'],
        headers: COMMON_HEADERS,
        query: [],
        pathParams: [{ name: 'user_id', type: 'number', required: true, values: '-', limit: '-', example: '2', desc: '用户 ID' }],
        body: [
          { name: 'name', type: 'string', required: false, values: '-', limit: '-', example: '杨壮', desc: '姓名' },
          { name: 'phone', type: 'string', required: false, values: '-', limit: '-', example: '13800000000', desc: '手机号' },
          { name: 'status', type: 'string', required: false, values: 'enabled / disabled', limit: '-', example: 'disabled', desc: '状态' },
        ],
        curl: `curl -X PATCH "${BASE}/users/2" \\
  -H "X-App-Id: hj_xxxxxxxx" \\
  -H "X-App-Date: Sat, 03 Oct 2026 12:00:00 GMT" \\
  -H "X-App-Authorization: HanJiang-1 hj_xxxxxxxx:{signature}" \\
  -H "Content-Type: application/json" \\
  -d '{"status":"disabled"}'`,
        responseFields: [
          ...COMMON_RESPONSE_FIELDS,
          { name: 'data.id', type: 'integer', required: false, values: '-', limit: '-', example: '2', desc: '用户 ID' },
          { name: 'data.username', type: 'string', required: false, values: '-', limit: '-', example: 'yangzhuang', desc: '用户名' },
          { name: 'data.status', type: 'string', required: false, values: 'enabled / disabled', limit: '-', example: 'disabled', desc: '更新后的状态' },
        ],
        responseExample: JSON.stringify(
          {
            code: 200,
            message: 'OK',
            data: { id: 2, username: 'yangzhuang', name: '杨壮', status: 'disabled' },
            timestamp: '2026-10-03T12:00:00Z',
            request_id: 'req_open_xxxxx',
          },
          null,
          2,
        ),
        responseDesc: '更新后的用户信息。',
      },
      {
        id: 'user-delete',
        name: '删除用户',
        method: 'DELETE',
        path: '/users/{user_id}',
        scope: 'user:write',
        summary: '软删除用户。',
        notes: ['软删除：数据保留但不可登录。'],
        limits: ['无。'],
        headers: COMMON_HEADERS,
        query: [],
        pathParams: [{ name: 'user_id', type: 'number', required: true, values: '-', limit: '-', example: '2', desc: '用户 ID' }],
        body: [],
        curl: `curl -X DELETE "${BASE}/users/2" \\
  -H "X-App-Id: hj_xxxxxxxx" \\
  -H "X-App-Date: Sat, 03 Oct 2026 12:00:00 GMT" \\
  -H "X-App-Authorization: HanJiang-1 hj_xxxxxxxx:{signature}" \\
  -H "Content-Type: application/json"`,
        responseFields: [
          ...COMMON_RESPONSE_FIELDS,
          { name: 'data.deleted', type: 'boolean', required: false, values: 'true', limit: '-', example: 'true', desc: '删除结果标记' },
        ],
        responseExample: JSON.stringify(
          {
            code: 200,
            message: 'OK',
            data: { deleted: true },
            timestamp: '2026-10-03T12:00:00Z',
            request_id: 'req_open_xxxxx',
          },
          null,
          2,
        ),
        responseDesc: '删除结果标记。',
      },
    ],
  },

  // ─────────────────────────── 角色管理 ───────────────────────────
  {
    key: 'role',
    name: '角色管理',
    desc: '角色核心数据的开放能力（需 role:read / role:write scope）。',
    apis: [
      {
        id: 'role-list',
        name: '角色列表',
        method: 'GET',
        path: '/roles',
        scope: 'role:read',
        summary: '分页查询角色列表，支持关键字 / 类型 / 状态过滤。',
        notes: ['page_size 最大 100。'],
        limits: ['keyword 按角色名称 / 编码模糊搜索。'],
        headers: COMMON_HEADERS,
        query: [
          { name: 'page', type: 'number', required: false, values: '-', limit: '从 1 开始', example: '1', desc: '页码（默认 1）' },
          { name: 'page_size', type: 'number', required: false, values: '-', limit: '1-100，默认 20', example: '20', desc: '每页条数' },
          { name: 'keyword', type: 'string', required: false, values: '-', limit: '-', example: '运维', desc: '角色名称 / 编码模糊搜索' },
          { name: 'role_type', type: 'string', required: false, values: 'system / custom', limit: '-', example: 'custom', desc: '角色类型过滤' },
          { name: 'status', type: 'string', required: false, values: 'enabled / disabled', limit: '-', example: 'enabled', desc: '状态过滤' },
        ],
        pathParams: [],
        body: [],
        curl: `curl -X GET "${BASE}/roles?page=1&page_size=20" \\
  -H "X-App-Id: hj_xxxxxxxx" \\
  -H "X-App-Date: Sat, 03 Oct 2026 12:00:00 GMT" \\
  -H "X-App-Authorization: HanJiang-1 hj_xxxxxxxx:{signature}" \\
  -H "Content-Type: application/json"`,
        responseFields: [
          ...COMMON_RESPONSE_FIELDS,
          { name: 'data.items', type: 'array[object]', required: false, values: '-', limit: '-', example: '[{id,role_name,role_code,role_type,status}]', desc: '角色列表' },
          { name: 'data.total', type: 'integer', required: false, values: '-', limit: '-', example: '3', desc: '总记录数' },
          { name: 'data.page', type: 'integer', required: false, values: '-', limit: '-', example: '1', desc: '当前页码' },
          { name: 'data.page_size', type: 'integer', required: false, values: '-', limit: '-', example: '20', desc: '每页条数' },
          { name: 'data.total_pages', type: 'integer', required: false, values: '-', limit: '-', example: '1', desc: '总页数' },
        ],
        responseExample: JSON.stringify(
          {
            code: 200,
            message: 'OK',
            data: {
              items: [
                { id: 1, role_name: '超级管理员', role_code: 'superadmin', role_type: 'system', status: 'enabled' },
              ],
              total: 1,
              page: 1,
              page_size: 20,
              total_pages: 1,
            },
            timestamp: '2026-10-03T12:00:00Z',
            request_id: 'req_open_xxxxx',
          },
          null,
          2,
        ),
        responseDesc: '分页结构 {items, total, page, page_size, total_pages}。',
      },
      {
        id: 'role-create',
        name: '创建角色',
        method: 'POST',
        path: '/roles',
        scope: 'role:write',
        summary: '创建角色（角色名称 / 编码全局唯一）。',
        notes: [
          '角色名称 / 编码重复返回 409（角色名称/编码 xxx 已存在）。',
          '权限绑定 / 解绑属管理端管理行为，开放接口不提供。',
        ],
        limits: ['role_name / role_code 1-50 位；description 最长 255。'],
        headers: COMMON_HEADERS,
        query: [],
        pathParams: [],
        body: [
          { name: 'role_name', type: 'string', required: true, values: '-', limit: '1-50 位', example: '运维角色', desc: '角色名称（唯一）' },
          { name: 'role_code', type: 'string', required: true, values: '-', limit: '1-50 位', example: 'ops', desc: '角色编码（唯一）' },
          { name: 'description', type: 'string', required: true, values: '-', limit: '最长 255', example: '负责平台运维', desc: '角色描述' },
          { name: 'role_type', type: 'string', required: false, values: 'system / custom', limit: '-', example: 'custom', desc: '角色类型（默认 custom）' },
          { name: 'status', type: 'string', required: false, values: 'enabled / disabled', limit: '-', example: 'enabled', desc: '状态（默认 enabled）' },
        ],
        curl: `curl -X POST "${BASE}/roles" \\
  -H "X-App-Id: hj_xxxxxxxx" \\
  -H "X-App-Date: Sat, 03 Oct 2026 12:00:00 GMT" \\
  -H "X-App-Authorization: HanJiang-1 hj_xxxxxxxx:{signature}" \\
  -H "Content-Type: application/json" \\
  -d '{"role_name":"运维角色","role_code":"ops","description":"负责平台运维"}'`,
        responseFields: [
          ...COMMON_RESPONSE_FIELDS,
          { name: 'data.id', type: 'integer', required: false, values: '-', limit: '-', example: '13', desc: '角色 ID' },
          { name: 'data.role_name', type: 'string', required: false, values: '-', limit: '-', example: '运维角色', desc: '角色名称' },
          { name: 'data.role_code', type: 'string', required: false, values: '-', limit: '-', example: 'ops', desc: '角色编码' },
          { name: 'data.role_type', type: 'string', required: false, values: 'system / custom', limit: '-', example: 'custom', desc: '角色类型' },
          { name: 'data.status', type: 'string', required: false, values: 'enabled / disabled', limit: '-', example: 'enabled', desc: '状态' },
        ],
        responseExample: JSON.stringify(
          {
            code: 201,
            message: 'OK',
            data: { id: 13, role_name: '运维角色', role_code: 'ops', description: '负责平台运维', role_type: 'custom', status: 'enabled' },
            timestamp: '2026-10-03T12:00:00Z',
            request_id: 'req_open_xxxxx',
          },
          null,
          2,
        ),
        responseDesc: '创建成功的角色信息。',
      },
      {
        id: 'role-get',
        name: '角色详情',
        method: 'GET',
        path: '/roles/{role_id}',
        scope: 'role:read',
        summary: '查询单个角色详情。',
        notes: ['角色不存在返回 404。'],
        limits: ['无。'],
        headers: COMMON_HEADERS,
        query: [],
        pathParams: [{ name: 'role_id', type: 'number', required: true, values: '-', limit: '-', example: '13', desc: '角色 ID' }],
        body: [],
        curl: `curl -X GET "${BASE}/roles/13" \\
  -H "X-App-Id: hj_xxxxxxxx" \\
  -H "X-App-Date: Sat, 03 Oct 2026 12:00:00 GMT" \\
  -H "X-App-Authorization: HanJiang-1 hj_xxxxxxxx:{signature}" \\
  -H "Content-Type: application/json"`,
        responseFields: [
          ...COMMON_RESPONSE_FIELDS,
          { name: 'data.id', type: 'integer', required: false, values: '-', limit: '-', example: '13', desc: '角色 ID' },
          { name: 'data.role_name', type: 'string', required: false, values: '-', limit: '-', example: '运维角色', desc: '角色名称' },
          { name: 'data.role_code', type: 'string', required: false, values: '-', limit: '-', example: 'ops', desc: '角色编码' },
          { name: 'data.status', type: 'string', required: false, values: 'enabled / disabled', limit: '-', example: 'enabled', desc: '状态' },
        ],
        responseExample: JSON.stringify(
          {
            code: 200,
            message: 'OK',
            data: { id: 13, role_name: '运维角色', role_code: 'ops', description: '负责平台运维', role_type: 'custom', status: 'enabled' },
            timestamp: '2026-10-03T12:00:00Z',
            request_id: 'req_open_xxxxx',
          },
          null,
          2,
        ),
        responseDesc: '角色详情；不存在时返回 404。',
      },
      {
        id: 'role-update',
        name: '更新角色',
        method: 'PATCH',
        path: '/roles/{role_id}',
        scope: 'role:write',
        summary: '更新角色信息（仅更新提供的字段）。',
        notes: ['字段全可选，仅更新传入字段。'],
        limits: ['无。'],
        headers: COMMON_HEADERS,
        query: [],
        pathParams: [{ name: 'role_id', type: 'number', required: true, values: '-', limit: '-', example: '13', desc: '角色 ID' }],
        body: [
          { name: 'role_name', type: 'string', required: false, values: '-', limit: '1-50 位', example: '运维角色', desc: '角色名称' },
          { name: 'description', type: 'string', required: false, values: '-', limit: '最长 255', example: '负责平台运维与监控', desc: '角色描述' },
          { name: 'status', type: 'string', required: false, values: 'enabled / disabled', limit: '-', example: 'disabled', desc: '状态' },
        ],
        curl: `curl -X PATCH "${BASE}/roles/13" \\
  -H "X-App-Id: hj_xxxxxxxx" \\
  -H "X-App-Date: Sat, 03 Oct 2026 12:00:00 GMT" \\
  -H "X-App-Authorization: HanJiang-1 hj_xxxxxxxx:{signature}" \\
  -H "Content-Type: application/json" \\
  -d '{"status":"disabled"}'`,
        responseFields: [
          ...COMMON_RESPONSE_FIELDS,
          { name: 'data.id', type: 'integer', required: false, values: '-', limit: '-', example: '13', desc: '角色 ID' },
          { name: 'data.role_name', type: 'string', required: false, values: '-', limit: '-', example: '运维角色', desc: '角色名称' },
          { name: 'data.status', type: 'string', required: false, values: 'enabled / disabled', limit: '-', example: 'disabled', desc: '更新后的状态' },
        ],
        responseExample: JSON.stringify(
          {
            code: 200,
            message: 'OK',
            data: { id: 13, role_name: '运维角色', role_code: 'ops', description: '负责平台运维与监控', role_type: 'custom', status: 'disabled' },
            timestamp: '2026-10-03T12:00:00Z',
            request_id: 'req_open_xxxxx',
          },
          null,
          2,
        ),
        responseDesc: '更新后的角色信息。',
      },
      {
        id: 'role-delete',
        name: '删除角色',
        method: 'DELETE',
        path: '/roles/{role_id}',
        scope: 'role:write',
        summary: '删除角色（软删除）。',
        notes: ['角色被用户引用时按后端约束处理。'],
        limits: ['无。'],
        headers: COMMON_HEADERS,
        query: [],
        pathParams: [{ name: 'role_id', type: 'number', required: true, values: '-', limit: '-', example: '13', desc: '角色 ID' }],
        body: [],
        curl: `curl -X DELETE "${BASE}/roles/13" \\
  -H "X-App-Id: hj_xxxxxxxx" \\
  -H "X-App-Date: Sat, 03 Oct 2026 12:00:00 GMT" \\
  -H "X-App-Authorization: HanJiang-1 hj_xxxxxxxx:{signature}" \\
  -H "Content-Type: application/json"`,
        responseFields: [
          ...COMMON_RESPONSE_FIELDS,
          { name: 'data.deleted', type: 'boolean', required: false, values: 'true', limit: '-', example: 'true', desc: '删除结果标记' },
        ],
        responseExample: JSON.stringify(
          {
            code: 200,
            message: 'OK',
            data: { deleted: true },
            timestamp: '2026-10-03T12:00:00Z',
            request_id: 'req_open_xxxxx',
          },
          null,
          2,
        ),
        responseDesc: '删除结果标记。',
      },
      {
        id: 'role-permissions',
        name: '角色权限列表',
        method: 'GET',
        path: '/roles/{role_id}/permissions',
        scope: 'role:read',
        summary: '查询角色已绑定的权限列表。',
        notes: ['权限绑定 / 解绑属管理端管理行为，开放接口仅提供只读查询。'],
        limits: ['无。'],
        headers: COMMON_HEADERS,
        query: [],
        pathParams: [{ name: 'role_id', type: 'number', required: true, values: '-', limit: '-', example: '1', desc: '角色 ID' }],
        body: [],
        curl: `curl -X GET "${BASE}/roles/1/permissions" \\
  -H "X-App-Id: hj_xxxxxxxx" \\
  -H "X-App-Date: Sat, 03 Oct 2026 12:00:00 GMT" \\
  -H "X-App-Authorization: HanJiang-1 hj_xxxxxxxx:{signature}" \\
  -H "Content-Type: application/json"`,
        responseFields: [
          ...COMMON_RESPONSE_FIELDS,
          { name: 'data.items', type: 'array[object]', required: false, values: '-', limit: '-', example: '[{id,perm_code,perm_name,module,operation}]', desc: '权限列表（含模块与操作）' },
          { name: 'data.total', type: 'integer', required: false, values: '-', limit: '-', example: '5', desc: '权限总数' },
        ],
        responseExample: JSON.stringify(
          {
            code: 200,
            message: 'OK',
            data: {
              items: [
                { id: 1, perm_code: 'user:read', perm_name: '查看用户', module: 'user', module_label: '用户管理', operation: 'read', operation_label: '查看' },
              ],
              total: 1,
            },
            timestamp: '2026-10-03T12:00:00Z',
            request_id: 'req_open_xxxxx',
          },
          null,
          2,
        ),
        responseDesc: '角色已绑定权限列表。',
      },
    ],
  },

  // ─────────────────────────── 文件管理 ───────────────────────────
  {
    key: 'file',
    name: '文件管理',
    desc: '文件上传 / 下载 / 删除的开放能力（需 file:read / file:write scope）。',
    apis: [
      {
        id: 'file-list',
        name: '文件列表',
        method: 'GET',
        path: '/files',
        scope: 'file:read',
        summary: '分页查询文件列表，支持目录 / 关键字过滤。',
        notes: ['page_size 最大 100。'],
        limits: ['keyword 按文件名模糊搜索。'],
        headers: COMMON_HEADERS,
        query: [
          { name: 'page', type: 'number', required: false, values: '-', limit: '从 1 开始', example: '1', desc: '页码（默认 1）' },
          { name: 'page_size', type: 'number', required: false, values: '-', limit: '1-100，默认 20', example: '20', desc: '每页条数' },
          { name: 'folder', type: 'string', required: false, values: '-', limit: '-', example: 'general', desc: '存储目录过滤' },
          { name: 'keyword', type: 'string', required: false, values: '-', limit: '-', example: '报表', desc: '文件名模糊搜索' },
        ],
        pathParams: [],
        body: [],
        curl: `curl -X GET "${BASE}/files?page=1&page_size=20" \\
  -H "X-App-Id: hj_xxxxxxxx" \\
  -H "X-App-Date: Sat, 03 Oct 2026 12:00:00 GMT" \\
  -H "X-App-Authorization: HanJiang-1 hj_xxxxxxxx:{signature}" \\
  -H "Content-Type: application/json"`,
        responseFields: [
          ...COMMON_RESPONSE_FIELDS,
          { name: 'data.items', type: 'array[object]', required: false, values: '-', limit: '-', example: '[{id,original_name,folder,size}]', desc: '文件列表' },
          { name: 'data.total', type: 'integer', required: false, values: '-', limit: '-', example: '2', desc: '总记录数' },
          { name: 'data.page', type: 'integer', required: false, values: '-', limit: '-', example: '1', desc: '当前页码' },
          { name: 'data.page_size', type: 'integer', required: false, values: '-', limit: '-', example: '20', desc: '每页条数' },
          { name: 'data.total_pages', type: 'integer', required: false, values: '-', limit: '-', example: '1', desc: '总页数' },
        ],
        responseExample: JSON.stringify(
          {
            code: 200,
            message: 'OK',
            data: {
              items: [{ id: 1, original_name: 'report.xlsx', folder: 'general', size: 10240 }],
              total: 1,
              page: 1,
              page_size: 20,
              total_pages: 1,
            },
            timestamp: '2026-10-03T12:00:00Z',
            request_id: 'req_open_xxxxx',
          },
          null,
          2,
        ),
        responseDesc: '分页结构 {items, total, page, page_size, total_pages}。',
      },
      {
        id: 'file-upload',
        name: '上传文件',
        method: 'POST',
        path: '/files',
        scope: 'file:write',
        summary: '上传文件（文件内容以 base64 编码内嵌 JSON body）。',
        notes: [
          '开放接口签名串固定 Content-Type: application/json 并对 body 做 SHA256 摘要，multipart 无法进入签名体系，故上传统一走 base64 内嵌。',
          'content_base64 非法或内容为空返回 422。',
        ],
        limits: ['filename 1-255 位（含扩展名）；folder 1-64 位（默认 general）。'],
        headers: COMMON_HEADERS,
        query: [],
        pathParams: [],
        body: [
          { name: 'filename', type: 'string', required: true, values: '-', limit: '1-255 位，含扩展名', example: 'report.xlsx', desc: '文件名' },
          { name: 'content_base64', type: 'string', required: true, values: '-', limit: '-', example: 'UEsDBBQABgAI...', desc: '文件内容（Base64 编码）' },
          { name: 'folder', type: 'string', required: false, values: '-', limit: '1-64 位', example: 'general', desc: '存储目录（默认 general）' },
        ],
        curl: `curl -X POST "${BASE}/files" \\
  -H "X-App-Id: hj_xxxxxxxx" \\
  -H "X-App-Date: Sat, 03 Oct 2026 12:00:00 GMT" \\
  -H "X-App-Authorization: HanJiang-1 hj_xxxxxxxx:{signature}" \\
  -H "Content-Type: application/json" \\
  -d '{"filename":"report.xlsx","folder":"general","content_base64":"UEsDBBQABgAI..."}'`,
        responseFields: [
          ...COMMON_RESPONSE_FIELDS,
          { name: 'data.id', type: 'integer', required: false, values: '-', limit: '-', example: '7', desc: '文件 ID' },
          { name: 'data.original_name', type: 'string', required: false, values: '-', limit: '-', example: 'report.xlsx', desc: '文件名' },
          { name: 'data.storage_key', type: 'string', required: false, values: '-', limit: '-', example: 'open/7/report.xlsx', desc: '存储 key（可用于下载）' },
        ],
        responseExample: JSON.stringify(
          {
            code: 201,
            message: 'OK',
            data: { id: 7, original_name: 'report.xlsx', storage_key: 'open/7/report.xlsx' },
            timestamp: '2026-10-03T12:00:00Z',
            request_id: 'req_open_xxxxx',
          },
          null,
          2,
        ),
        responseDesc: '上传成功的文件信息（storage_key 可作下载路径）。',
      },
      {
        id: 'file-get',
        name: '下载文件',
        method: 'GET',
        path: '/files/{file_path:path}',
        scope: 'file:read',
        summary: '下载文件（按存储 key 或相对路径）。',
        notes: [
          '本地存储返回文件流；云存储返回 302 重定向 URL。',
          'file_path 为存储 key（如 open/7/report.xlsx）或相对路径。',
        ],
        limits: ['无。'],
        headers: COMMON_HEADERS,
        query: [],
        pathParams: [{ name: 'file_path', type: 'string', required: true, values: '-', limit: 'path 通配', example: 'open/7/report.xlsx', desc: '文件路径（存储 key 或相对路径）' }],
        body: [],
        curl: `curl -X GET "${BASE}/files/open/7/report.xlsx" \\
  -H "X-App-Id: hj_xxxxxxxx" \\
  -H "X-App-Date: Sat, 03 Oct 2026 12:00:00 GMT" \\
  -H "X-App-Authorization: HanJiang-1 hj_xxxxxxxx:{signature}" \\
  -H "Content-Type: application/json"`,
        responseFields: [
          ...COMMON_RESPONSE_FIELDS,
          { name: 'data', type: 'file', required: false, values: '-', limit: '-', example: '文件流 / 302', desc: '文件内容（二进制流）或重定向 URL' },
        ],
        responseExample: '（二进制文件流；云存储时 HTTP 302 重定向到预签名 URL）',
        responseDesc: '文件不存在时返回 404。',
      },
      {
        id: 'file-delete',
        name: '删除文件',
        method: 'DELETE',
        path: '/files/{file_id}',
        scope: 'file:write',
        summary: '删除文件（软删除）。',
        notes: ['文件不存在返回 404。'],
        limits: ['无。'],
        headers: COMMON_HEADERS,
        query: [],
        pathParams: [{ name: 'file_id', type: 'number', required: true, values: '-', limit: '-', example: '7', desc: '文件 ID' }],
        body: [],
        curl: `curl -X DELETE "${BASE}/files/7" \\
  -H "X-App-Id: hj_xxxxxxxx" \\
  -H "X-App-Date: Sat, 03 Oct 2026 12:00:00 GMT" \\
  -H "X-App-Authorization: HanJiang-1 hj_xxxxxxxx:{signature}" \\
  -H "Content-Type: application/json"`,
        responseFields: [
          ...COMMON_RESPONSE_FIELDS,
          { name: 'data.deleted', type: 'boolean', required: false, values: 'true', limit: '-', example: 'true', desc: '删除结果标记' },
        ],
        responseExample: JSON.stringify(
          {
            code: 200,
            message: 'OK',
            data: { deleted: true },
            timestamp: '2026-10-03T12:00:00Z',
            request_id: 'req_open_xxxxx',
          },
          null,
          2,
        ),
        responseDesc: '删除结果标记。',
      },
    ],
  },
]

/** 按模块 key 快速索引 */
export const capabilityModuleMap = Object.fromEntries(capabilityModules.map(m => [m.key, m])) as Record<
  CapabilityModule['key'],
  CapabilityModule
>

/** 全部开放接口数量（供首页统计） */
export const totalCapabilityApis = capabilityModules.reduce((sum, m) => sum + m.apis.length, 0)
