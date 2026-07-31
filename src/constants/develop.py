"""
开发相关常量

本模块定义了开发过程中常用的常量（HTTP 内容类型）。
加密相关常量已移除，避免在模板中保留未使用代码；
如需密码学算法，请按业务场景自行引入 cryptography/argon2 等库。
"""

# HTTP 内容类型
JSON_CONTENT_TYPE = "application/json"
FILE_CONTENT_TYPE = "application/octet-stream"
FORM_URL_ENCODED_CONTENT_TYPE = "application/x-www-form-urlencoded"
MULTIPART_FORM_DATA_CONTENT_TYPE = "multipart/form-data"
