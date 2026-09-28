"""AI 助手 API。

提供：
    - POST /assistant/chat                     SSE 流式对话（JWT 鉴权，仅要求登录）
    - POST /assistant/conversations            创建会话
    - GET  /assistant/conversations            会话列表
    - GET  /assistant/conversations/{id}/messages  会话消息列表
    - POST /assistant/feedback                 👍👎 反馈收集

SSE 通道说明：chat 接口返回 text/event-stream，事件为 data: <json> 单行格式；
事件类型见 AssistantEventType（token / navigate / denied / error / done）。
该接口不使用统一 success_response 包装（属 SSE 通道特例），其余接口保持统一响应。
"""

import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from src.api.api_permission_decorator import permission
from src.api.dependencies import get_assistant_service, get_current_user
from src.api.response import success_response
from src.constants.assistant import (
    ASSISTANT_PERMISSION_CHAT,
    ASSISTANT_PERMISSION_FEEDBACK,
    AssistantEventType,
)
from src.core.logger import logger
from src.models.entities.assistant_entity import (
    AssistantConversationEntity,
    AssistantMessageEntity,
)
from src.schemas.assistant import (
    ChatRequest,
    ConversationPinRequest,
    ConversationResponse,
    FeedbackRequest,
    MessageResponse,
)
from src.schemas.auth import CurrentUser
from src.services.assistant_service import AssistantService

router = APIRouter(prefix="/assistant", tags=["AI 助手"])

#: SSE 响应头：禁止代理缓冲，保证事件即时下发
_SSE_HEADERS: dict[str, str] = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def _sse_event(data: dict[str, object]) -> str:
    """将事件字典序列化为 SSE 数据帧。

    Args:
        data: 事件字典

    Returns:
        str: 完整 SSE 帧（data: <json>\\n\\n）
    """
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _to_conversation_response(entity: AssistantConversationEntity) -> ConversationResponse:
    """会话实体转响应模型。

    Args:
        entity: 会话实体

    Returns:
        ConversationResponse: 会话响应模型
    """
    return ConversationResponse.model_validate(entity)


def _to_message_response(entity: AssistantMessageEntity) -> MessageResponse:
    """消息实体转响应模型。

    Args:
        entity: 消息实体

    Returns:
        MessageResponse: 消息响应模型
    """
    return MessageResponse.model_validate(entity)


@router.post(
    "/chat",
    summary="AI 助手对话（SSE 流式）",
    description="流式返回回复文本与跳转指令；仅要求登录，不强制权限（系统全部登录用户可用）",
    response_class=StreamingResponse,
)
@permission(ASSISTANT_PERMISSION_CHAT, "AI助手对话", "assistant", "chat")
def chat(
    body: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: AssistantService = Depends(get_assistant_service),
) -> StreamingResponse:
    """AI 助手对话接口（SSE 事件流）。

    Args:
        body: 对话请求体
        current_user: 当前登录用户
        service: AI 助手编排服务

    Returns:
        StreamingResponse: SSE 流式响应
    """

    def generate() -> Iterator[str]:
        """事件流生成器：服务事件直通，通道兜底仅处理不可预期异常。

        业务异常（功能未启用 / 会话不存在 / 大模型服务异常）已在 services 层
        内部转为 error + done 事件，此处 except 只作为 SSE 通道的最后防线，
        防止不可预期异常导致流中断无响应。
        """
        try:
            for event in service.chat_stream(current_user, body.conversation_id, body.message):
                yield _sse_event(event)
        except Exception as exc:  # noqa: BLE001 - SSE 通道最后防线，仅兜底不可预期异常
            logger.error(f"AI 助手 SSE 通道异常: {exc}")
            yield _sse_event({"type": AssistantEventType.ERROR.mark, "message": "服务异常，请稍后再试"})
            yield _sse_event(
                {
                    "type": AssistantEventType.DONE.mark,
                    "conversation_id": body.conversation_id,
                    "message_id": None,
                }
            )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.post(
    "/conversations",
    summary="创建会话",
    description="创建一个新的 AI 助手会话",
)
@permission(ASSISTANT_PERMISSION_CHAT, "AI助手对话", "assistant", "chat")
def create_conversation(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: AssistantService = Depends(get_assistant_service),
) -> JSONResponse:
    """创建会话接口。

    Args:
        request: 当前请求对象
        current_user: 当前登录用户
        service: AI 助手编排服务

    Returns:
        统一响应结构，data 为新建会话详情
    """
    entity = service.create_conversation(current_user.id)
    return success_response(_to_conversation_response(entity), request)


@router.get(
    "/conversations",
    summary="会话列表",
    description="查询当前用户的 AI 助手会话列表",
)
@permission(ASSISTANT_PERMISSION_CHAT, "AI助手对话", "assistant", "chat")
def list_conversations(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: AssistantService = Depends(get_assistant_service),
) -> JSONResponse:
    """会话列表接口。

    Args:
        request: 当前请求对象
        current_user: 当前登录用户
        service: AI 助手编排服务

    Returns:
        统一响应结构，data 为会话列表
    """
    conversations = service.list_conversations(current_user.id)
    return success_response(
        [_to_conversation_response(item) for item in conversations],
        request,
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    summary="会话消息列表",
    description="查询指定会话的消息列表（校验归属）",
)
@permission(ASSISTANT_PERMISSION_CHAT, "AI助手对话", "assistant", "chat")
def list_conversation_messages(
    conversation_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: AssistantService = Depends(get_assistant_service),
) -> JSONResponse:
    """会话消息列表接口。

    Args:
        conversation_id: 会话ID
        request: 当前请求对象
        current_user: 当前登录用户
        service: AI 助手编排服务

    Returns:
        统一响应结构，data 为消息列表（时间正序）
    """
    messages = service.list_messages(conversation_id, current_user.id)
    return success_response(
        [_to_message_response(item) for item in messages],
        request,
    )


@router.delete(
    "/conversations/{conversation_id}",
    summary="删除会话",
    description="软删除指定会话（标记 deleted_at，消息与反馈保留留档；校验归属）",
)
@permission(ASSISTANT_PERMISSION_CHAT, "AI助手对话", "assistant", "chat")
def delete_conversation(
    conversation_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: AssistantService = Depends(get_assistant_service),
) -> JSONResponse:
    """删除会话接口。

    Args:
        conversation_id: 会话ID
        request: 当前请求对象
        current_user: 当前登录用户
        service: AI 助手编排服务

    Returns:
        统一响应结构，data 为空
    """
    service.delete_conversation(current_user.id, conversation_id)
    return success_response(None, request)


@router.post(
    "/conversations/{conversation_id}/pin",
    summary="置顶 / 取消置顶会话",
    description="设置会话置顶状态（校验归属）",
)
@permission(ASSISTANT_PERMISSION_CHAT, "AI助手对话", "assistant", "chat")
def pin_conversation(
    conversation_id: int,
    body: ConversationPinRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: AssistantService = Depends(get_assistant_service),
) -> JSONResponse:
    """置顶会话接口。

    Args:
        conversation_id: 会话ID
        body: 置顶请求体
        request: 当前请求对象
        current_user: 当前登录用户
        service: AI 助手编排服务

    Returns:
        统一响应结构，data 为更新后的会话详情
    """
    entity = service.update_pinned(current_user.id, conversation_id, body.pinned)
    return success_response(_to_conversation_response(entity), request)


@router.post(
    "/feedback",
    summary="消息反馈",
    description="用户对助手回复进行 👍👎 反馈（提示词调优数据源）",
)
@permission(ASSISTANT_PERMISSION_FEEDBACK, "AI助手反馈", "assistant", "feedback")
def submit_feedback(
    body: FeedbackRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: AssistantService = Depends(get_assistant_service),
) -> JSONResponse:
    """消息反馈接口。

    Args:
        body: 反馈请求体
        request: 当前请求对象
        current_user: 当前登录用户
        service: AI 助手编排服务

    Returns:
        统一响应结构，data 为空
    """
    service.save_feedback(current_user.id, body)
    return success_response(None, request)
