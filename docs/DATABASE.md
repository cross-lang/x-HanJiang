# 数据库配置指南

寒江（HanJiang）默认基于 SQLAlchemy 2.0 + PyMySQL，支持 MySQL 与 PostgreSQL。

## 1. 连接字符串格式

### MySQL

```
DATABASE_URL=mysql+pymysql://<user>:<password>@<host>:<port>/<database>?charset=utf8mb4
```

如果省略驱动前缀（`mysql://`），代码会自动转换为 `mysql+pymysql://`。

### PostgreSQL

```
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<database>
```

## 2. 配置项

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| 数据库连接 | `DATABASE_URL` | 空 | 留空表示禁用数据库 |
| 连接池大小 | `DATABASE_POOL_SIZE` | 5 | 同时维持的连接数 |
| 连接回收 | (硬编码) | 3600s | 防止 MySQL wait_timeout 断开 |
| 健康检查 | `pool_pre_ping` | True | 自动剔除失效连接 |

## 3. 数据库迁移（Alembic）

项目已集成 Alembic，用于管理表结构变更：

```bash
# 生成新迁移
uv run alembic revision --autogenerate -m "add xxx"

# 应用迁移
uv run alembic upgrade head

# 回滚一步
uv run alembic downgrade -1

# 查看当前版本
uv run alembic current
```

迁移文件位于 `alembic/versions/`。每次表结构变更必须生成新迁移，禁止直接
`Base.metadata.create_all`。

## 4. 初始化脚本

仅用于首次部署或测试环境：

```bash
uv run python scripts/init_db.py
```

> 生产环境务必使用 Alembic，避免 `create_all` 与已有结构产生不一致。

## 5. 字符集

MySQL 推荐使用 `utf8mb4` 与 `utf8mb4_unicode_ci`，确保 emoji 与多语言正常存储。
docker-compose 中已显式配置：

```yaml
command:
  - --character-set-server=utf8mb4
  - --collation-server=utf8mb4_unicode_ci
```

## 6. 事务与异常

- `get_db_session` (FastAPI Depends) 在请求结束时自动 `commit` / `rollback`。
- 唯一约束冲突会被 Repository 捕获并包装为 `ConflictException`（HTTP 409）。
- 其他数据库错误会被包装为 `DatabaseException`（HTTP 500）。
- 生产环境的 `DatabaseException` 默认不返回 details，避免泄漏内部栈。