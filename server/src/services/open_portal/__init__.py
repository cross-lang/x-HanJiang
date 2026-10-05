"""开放平台门户域业务逻辑包。

承载开放平台门户（/api/open-portal/v1，供 web/open_portal 前端调用）相关服务：
- auth_service：开发者认证（有状态会话：JWT + Redis 登录态，登出/改密/刷新可撤销）；
- developer_service：开发者资料与认证申请；
- app_service：开发者应用管理（owner 隔离 + 申请-审批流）。

开放接口网关鉴权见 src/services/open/gateway_service.py（/api/open/v1，AppId/Key 签名）。
"""
