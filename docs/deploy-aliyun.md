# 汉江（HanJiang）阿里云轻量应用服务器部署指南

> 经济实惠的单机演示部署：一台 2C4G 轻量应用服务器，Docker Compose 一键拉起全部服务，IP 直访（无域名 / HTTPS）。

## 架构

```
浏览器 ── http://<服务器IP>
              │
        ┌─────▼─────┐
        │  nginx:80  │  前端托管 + 统一入口
        │            │  /           → 管理系统前端 SPA
        │            │  /portal/    → 开放平台门户 SPA
        └─────┬──────┘  /api/        → 反代后端（注入 X-Real-IP）
              │
        ┌─────▼─────┐   ┌─────────┐   ┌─────────┐
        │  app:8000  │──▶│ mysql:8 │   │ redis:7 │
        │  FastAPI   │   └─────────┘   └─────────┘
        └────────────┘   （三者均随 docker-compose 编排，同机自建）
```

- 前端构建在 `web/Dockerfile` 内完成（Node 多阶段构建），服务器无需安装 Node
- 数据库初始化在应用启动时自动完成（`init_db` 建表 + `init_seed_data` 种子数据），无需手动迁移
- MySQL / Redis 为容器自建，数据持久化在 `mysql_data` / `redis_data` 卷

## 一、前置条件

| 项 | 要求 |
|---|---|
| 服务器 | 阿里云**轻量应用服务器** 2核4G（2G 会因 compose 资源上限合计约 2.5G 而 OOM） |
| 镜像 | Alibaba Cloud Linux 3 或 Ubuntu 24.04 |
| 安全组/防火墙 | 放行 **80**（HTTP）与 **22**（SSH）；8000/3306/6379 均不对外 |
| 本地 | 代码已推送到 Git 仓库（Gitee / GitHub 均可） |

## 二、初始化服务器（安装 Docker）

SSH 登录服务器后执行：

```bash
# 安装 Docker（官方一键脚本，Alibaba Cloud Linux / Ubuntu 通用）
curl -fsSL https://get.docker.com | bash
sudo systemctl enable --now docker

# 验证（Docker Compose V2 已内置于 docker 插件）
sudo docker compose version

# （可选）免 sudo 运行 docker
sudo usermod -aG docker $USER && newgrp docker
```

> 国内拉取镜像慢时，可在 `/etc/docker/daemon.json` 配置镜像加速地址（阿里云容器镜像服务控制台提供专属加速器）。

**2G 内存套餐附加步骤：添加 2G swap 兜底（防偶发 OOM）**

```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile \
  && sudo mkswap /swapfile && sudo swapon /swapfile \
  && echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 三、获取代码

```bash
sudo mkdir -p /opt/x-HanJiang && cd /opt/x-HanJiang
git clone <你的仓库地址> .
```

> 无 Git 条件时，可在本地打包上传：`git archive -o /tmp/hanjiang.tar HEAD`，再 `scp /tmp/hanjiang.tar user@<服务器IP>:/opt/x-HanJiang/` 解压。

## 四、准备环境变量

在**项目根目录**（与 `docker-compose.yml` 同级）创建 `.env`：

```bash
cd /opt/x-HanJiang
cat > .env <<'EOF'
APP_ENV=production

# JWT 密钥：必须 ≥32 字符随机串（用下面命令生成，勿用示例占位符）
AUTH_SECRET_KEY=<openssl rand -hex 32 的输出>

# 数据库（MYSQL_USER 默认 root 时，MYSQL_PASSWORD 必须与 MYSQL_ROOT_PASSWORD 一致）
MYSQL_ROOT_PASSWORD=<强密码1>
MYSQL_PASSWORD=<强密码1>
MYSQL_DATABASE=hanjiang

# Redis
REDIS_PASSWORD=<强密码2>

# AI 助手大模型密钥（小米 MiMo / DeepSeek 等 OpenAI 兼容平台）
AI_LLM_API_KEY=<你的 key>
EOF

# 生成随机密钥：
openssl rand -hex 32
```

> Gunicorn worker 数默认 4；若服务器内存吃紧，在 `.env` 追加 `GUNICORN_WORKERS=2`。

## 五、构建并启动

```bash
cd /opt/x-HanJiang
docker compose up -d --build
```

首次构建约 5~15 分钟（前端 npm ci + 后端 uv sync 均有 Docker 层缓存，二次构建很快）。

## 六、验证

| 检查项 | 地址 | 预期 |
|---|---|---|
| 容器健康 | `docker compose ps` | app / nginx / mysql / redis 全部 running（healthy） |
| 管理系统 | `http://<服务器IP>/` | 登录页正常渲染 |
| 开放平台门户 | `http://<服务器IP>/portal/` | 门户首页正常渲染 |
| API 文档 | `http://<服务器IP>/docs` | Swagger 页面打开 |
| 健康检查 | `http://<服务器IP>/api/admin/v1/health` | 返回健康状态 |

初始管理员账号（种子数据自动创建）：`superadmin` / `admin@123456`
**登录后请立即修改密码**（个人中心 → 修改密码）。

## 七、日常运维

```bash
# 查看日志
docker compose logs -f app        # 后端
docker compose logs -f nginx      # 前端与访问入口

# 更新部署（代码变更后）
git pull
docker compose up -d --build

# 重启 / 停止
docker compose restart app
docker compose down               # 不删数据卷
docker compose down -v            # 危险：连数据库数据一并删除

# 数据备份（演示环境定期执行即可）
docker compose exec mysql sh -c 'mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" hanjiang' > backup_$(date +%F).sql
```

## 八、常见问题

| 现象 | 原因与处理 |
|---|---|
| app 容器反复重启 | 内存不足：`.env` 追加 `GUNICORN_WORKERS=2` 后 `docker compose up -d` |
| 页面 502 | app 尚未通过健康检查或已崩溃：`docker compose logs app` 排查；nginx 依赖 `service_healthy` 会自动等待 |
| AI 助手报错 / 不回复 | `.env` 中 `AI_LLM_API_KEY` 未配置或失效；密钥经环境变量注入，改后需 `docker compose up -d` 重建 app |
| 构建时 npm/uv 超时 | 网络问题：为 Docker 配置镜像加速，或重试（层缓存会跳过已成功步骤） |
| 日志文件在哪 | app 容器 `/app/logs/`（按小时切割）；`docker compose exec app ls logs` 查看 |
| 安全提醒 | 演示结束建议 `docker compose down` 停机释放费用；`/docs` 路由如不需要可在 `web/nginx.conf` 删除对应 location |
