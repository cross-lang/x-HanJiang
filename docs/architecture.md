# 寒江（HanJiang）架构文档

## 1. 目录结构

```
x-HanJiang/
├── config/                  # 配置文件目录
│   ├── config.yaml          # 默认配置
│   ├── config.dev.yaml      # 开发环境覆盖
│   ├── config.test.yaml     # 测试环境覆盖
│   ├── config.prod.yaml     # 生产环境覆盖
│   └── .env.example         # 环境变量示例
├── docs/                    # 项目文档
├── examples/                # 使用示例
├── scripts/                 # 部署和工具脚本
├── src/                     # 核心业务代码
│   ├── api/                 # API 接口层
│   │   ├── dependencies.py  # 通用依赖注入
│   │   ├── health.py        # 健康检查接口
│   │   ├── user.py          # 用户管理接口
│   │   └── router.py        # 路由注册中心
│   ├── common/              # 公共组件
│   │   ├── base_model.py    # Pydantic 基础模型
│   │   ├── constants.py     # 全局常量
│   │   └── response.py      # 标准化响应格式
│   ├── constants/           # 业务常量
│   │   └── develop.py       # 开发相关常量
│   ├── core/                # 核心支撑层
│   │   ├── config.py        # 配置管理
│   │   ├── container.py     # 依赖注入容器
│   │   ├── exceptions.py    # 异常层级定义
│   │   ├── logger.py        # 日志管理
│   │   └── middleware.py    # HTTP 中间件
│   ├── models/              # 数据模型
│   │   ├── health.py        # 健康检查模型
│   │   └── user.py          # 用户模型
│   ├── repositories/        # 数据访问层
│   │   ├── base_repository.py  # 抽象基类
│   │   └── user_repository.py  # 用户实现
│   ├── services/            # 业务逻辑层
│   │   ├── base_service.py  # 抽象基类
│   │   └── user_service.py  # 用户实现
│   ├── utils/               # 工具函数
│   │   └── helpers.py       # 通用工具
│   └── main.py              # 应用入口
└── tests/                   # 测试代码
    ├── api/                 # API 测试
    ├── common/              # 公共组件测试
    └── core/                # 核心模块测试
```

## 2. 系统分层架构

```
┌─────────────────────────────────────────────┐
│                  Client                      │
│            (Browser / API Client)            │
└──────────────────┬──────────────────────────┘
                   │ HTTP Request
                   ▼
┌─────────────────────────────────────────────┐
│              Middleware Layer                │
│  ┌────────────┐ ┌──────────┐ ┌───────────┐  │
│  │ Request ID  │ │   CORS   │ │ Rate Limit│  │
│  └────────────┘ └──────────┘ └───────────┘  │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│               API Layer (api/)              │
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐  │
│  │  health   │ │   user   │ │  custom...  │  │
│  └──────────┘ └──────────┘ └─────────────┘  │
│         Request Validation (Pydantic)        │
└──────────────────┬──────────────────────────┘
                   │ API → Service (单向依赖)
                   ▼
┌─────────────────────────────────────────────┐
│            Service Layer (services/)          │
│  ┌──────────────────────────────────────┐   │
│  │        Business Logic                │   │
│  │  - 数据校验  - 业务规则  - 流程编排    │   │
│  └──────────────────────────────────────┘   │
└──────────────────┬──────────────────────────┘
                   │ Service → Repository (单向依赖)
                   ▼
┌─────────────────────────────────────────────┐
│          Repository Layer (repositories/)      │
│  ┌──────────────────────────────────────┐   │
│  │        Data Access                   │   │
│  │  - CRUD  - 查询  - 数据映射           │   │
│  └──────────────────────────────────────┘   │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│          External Storage / Database         │
│      (MySQL / PostgreSQL / Redis / MQ)       │
└─────────────────────────────────────────────┘
```

## 3. 核心支撑层

```
┌─────────────────────────────────────────────┐
│              Core Layer (core/)              │
├──────────┬──────────┬───────────┬───────────┤
│  Config   │  Logger  │ Exception │ Container │
│          │          │           │           │
│ Settings  │ loguru   │ AppExcept │ DI 容器   │
│ .env+yaml │ 请求ID   │ BusinessException   │
│ 多环境    │ 双输出   │ SystemException     │
│           │          │ 全局处理器 │ 自动装配  │
└──────────┴──────────┴───────────┴───────────┘
```

## 4. 配置加载优先级

```
环境变量 (.env)  >  环境特定 YAML  >  默认 YAML  >  代码默认值
  (最高优先级)    (config.{env}.yaml)  (config.yaml)
```

## 5. 依赖注入流程

```
1. Container.register(Interface, Implementation, Lifecycle)
   ↓ 注册接口到实现类的映射

2. Container.resolve(Interface)
   ↓ 查找注册表

3. Container._wire(Implementation)
   ↓ inspect 构造函数签名

4. 递归 resolve 每个构造函数参数
   ↓ 创建完整依赖链

5. 根据 Lifecycle 缓存或返回新实例
```

## 6. 标准响应格式

### 成功响应
```json
{
    "code": 200,
    "message": "success",
    "data": { ... },
    "timestamp": "2026-04-02T12:00:00+00:00",
    "request_id": "uuid-string"
}
```

### 分页响应
```json
{
    "code": 200,
    "message": "success",
    "data": [ ... ],
    "timestamp": "...",
    "request_id": "...",
    "pagination": {
        "total": 100,
        "page": 1,
        "page_size": 20,
        "total_pages": 5
    }
}
```

### 错误响应
```json
{
    "code": 400,
    "message": "Business error description",
    "data": null,
    "timestamp": "...",
    "request_id": "..."
}
```

## 7. 异常层级

```
AppException (基类)
├── BusinessException (4xx)
│   ├── ValidationException (422)    - 参数校验失败
│   ├── AuthenticationException (401) - 认证失败
│   ├── AuthorizationException (403)  - 权限不足
│   └── NotFoundException (404)      - 资源不存在
└── SystemException (5xx)
    ├── DatabaseException (500)       - 数据库错误
    └── ExternalServiceException (502) - 外部服务错误
```
