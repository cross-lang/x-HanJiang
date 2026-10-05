"""开放接口（网关）域业务逻辑包。

仅承载开放接口域（/api/open/v1，供外部应用调用）相关服务：
- gateway_service：应用身份鉴权（X-App-Id/App-Key 明文 或 HanJiang-1 签名）+ 审批门槛 + 协议函数。

开放 API服务（开发者账号/资料/应用管理）见 src/services/open_portal/，
管理端应用 CRUD/审批见 src/services/admin/openapi_app_service.py。
"""
