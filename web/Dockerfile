# 汉江（HanJiang）前端镜像：Node 构建两个 SPA + Nginx 托管
# 构建上下文为 web/ 目录（docker-compose.yml 的 build.context=./web）。
# 同域路由规划（详见 nginx.conf）：
#   /admin/       → 管理系统前端（web/admin，vite base=/admin/）
#   /open-portal/ → 开放平台门户前端（web/open_portal，vite base=/open-portal/）

# ==========================================
# Stage 1: 构建管理系统前端（web/admin）
# ==========================================
FROM node:20-alpine AS admin-builder
WORKDIR /build

# 先复制依赖声明并安装（利用层缓存：依赖不变时跳过 npm ci）
COPY admin/package.json admin/package-lock.json ./admin/
RUN cd admin && npm ci

COPY admin/ ./admin/
RUN cd admin && npm run build

# ==========================================
# Stage 2: 构建开放平台门户前端（web/open_portal）
# ==========================================
FROM node:20-alpine AS portal-builder
WORKDIR /build

COPY open_portal/package.json open_portal/package-lock.json ./open_portal/
RUN cd open_portal && npm ci

COPY open_portal/ ./open_portal/
RUN cd open_portal && npm run build

# ==========================================
# Stage 3: Nginx 托管两个 SPA 的静态产物
# ==========================================
FROM nginx:1.27-alpine

# 同域路由配置（覆盖默认站点配置）
COPY nginx.conf /etc/nginx/conf.d/default.conf

# admin 产物放 admin/ 子目录（挂 /admin/ 路由，vite base=/admin/）
COPY --from=admin-builder /build/admin/dist/ /usr/share/nginx/html/admin/
# open_portal 产物放 open-portal/ 子目录（挂 /open-portal/ 路由，vite base=/open-portal/）
COPY --from=portal-builder /build/open_portal/dist/ /usr/share/nginx/html/open-portal/

EXPOSE 80
