"""开放接口：文件上传请求模型（base64 JSON，兼容 HanJiang-1 签名协议）。"""

from pydantic import BaseModel, Field


class OpenFileUploadRequest(BaseModel):
    """开放接口文件上传请求（文件内容以 base64 编码内嵌 JSON body）。

    说明：开放接口鉴权签名串固定 Content-Type: application/json 并对 body 做
    SHA256 摘要，multipart 无法进入签名体系，故文件上传统一走 base64 内嵌。
    """

    filename: str = Field(min_length=1, max_length=255, description="文件名（含扩展名）")
    content_base64: str = Field(min_length=1, description="文件内容（Base64 编码）")
    folder: str = Field(default="general", min_length=1, max_length=64, description="存储目录（默认 general）")
