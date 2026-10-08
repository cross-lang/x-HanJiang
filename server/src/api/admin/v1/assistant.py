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

from collections.abc import Iterator

import asyncio
import time

from anyio.from_thread import run as _run_from_thread
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from src.api.admin.dependencies import (
    get_assistant_service,
    get_current_user,
    get_user_operator_context,
)
from src.api.admin.permission_decorator import permission
from src.api.response import success_response
from src.constants.assistant import AssistantEventType
from src.constants.enums import HttpContentType
from src.constants.permissions import PermissionCode
from src.core.config import settings
from src.core.logger import logger
from src.schemas.admin.assistant import (
    ChatRequest,
    ConversationPinRequest,
    ConversationResponse,
    FeedbackRequest,
    MessageResponse,
)
from src.schemas.admin.auth import CurrentUser
from src.services.admin.assistant_service import AssistantService
from src.utils.sse import build_sse_event

router = APIRouter(prefix="/assistant", tags=["管理系统：AI 助手"])

#: SSE 响应头：禁止代理缓冲，保证事件即时下发
_SSE_HEADERS: dict[str, str] = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}
#: 客户端断连检测间隔（秒）：节流调用 request.is_disconnected()，避免逐 chunk 检测带来的额外等待
_DISCONNECT_CHECK_INTERVAL: float = 2.0
#: 单次断连检测的等待上限（秒）：is_disconnected() 在客户端仍连接时会阻塞等待 http.disconnect，
#: 用 wait_for 设短超时，超时即视为仍连接，单次检测开销 ≤ 该值
_DISCONNECT_PROBE_TIMEOUT: float = 0.02


async def _probe_disconnect_async(request: Request) -> bool:
    """在事件循环中检测客户端是否已断开（带短超时，避免阻塞）。"""
    try:
        return await asyncio.wait_for(request.is_disconnected(), timeout=_DISCONNECT_PROBE_TIMEOUT)
    except asyncio.TimeoutError:
        return False


def _is_client_disconnected(request: Request) -> bool:
    """同步路由中检测客户端断连。

    同步路由运行在线程池中，通过 anyio 提供的 portal 将协程调度到主事件循环执行。
    任何异常均按「仍连接」处理（fail-open），避免误杀正常请求。
    """
    try:
        return _run_from_thread(_probe_disconnect_async, request)
    except Exception:  # noqa: BLE001 - 检测失败不影响主流程
        return False


@router.post(
    "/chat",
    summary="AI 助手对话（SSE 流式）",
    description="流式返回回复文本与跳转指令；仅要求登录，不强制权限（系统全部登录用户可用）",
    response_class=StreamingResponse,
)
@permission(PermissionCode.ASSISTANT_CHAT)
def chat(
    body: ChatRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: AssistantService = Depends(get_assistant_service),
) -> StreamingResponse:
    """AI 助手对话接口（SSE 事件流）。

    Args:
        body: 对话请求体
        request: 当前请求对象（构造操作人上下文，含 navigate 审计所需客户端 IP）
        current_user: 当前登录用户
        service: AI 助手编排服务

    Returns:
        StreamingResponse: SSE 流式响应
    """
    # 统一走操作人上下文工厂（纯数据字典，不含 Request 对象，可安全透传至 service 层）
    operator = get_user_operator_context(current_user, request)

    def generate() -> Iterator[str]:
        """事件流生成器：服务事件直通，通道兜底仅处理不可预期异常。

        业务异常（功能未启用 / 会话不存在 / 大模型服务异常）已在 services 层
        内部转为 error + done 事件，此处 except 只作为 SSE 通道的最后防线，
        防止不可预期异常导致流中断无响应。

        额外通道级保护：
            - 请求级超时：整轮对话（含多轮 tool call）超过 chat_request_timeout_seconds
              时主动下发 error + done 并终止，防止线程被长期占用。
            - 客户端断连感知：节流检测 request.is_disconnected()，客户端关闭页面后
              及时终止服务端生成，避免浪费大模型 token 与线程资源。
        """
        start_time = time.monotonic()
        request_timeout = settings.ai.llm.chat_request_timeout_seconds
        last_disconnect_check = 0.0
        try:
            for event in service.chat_stream(
                current_user,
                body.conversation_id,
                body.message,
                operator=operator,
            ):
                now = time.monotonic()
                # 1. 请求级超时：在事件边界检查，超时则主动结束
                if now - start_time > request_timeout:
                    logger.warning(
                        f"AI 助手对话超时（>{request_timeout}s），主动终止；"
                        f"conversation={body.conversation_id}"
                    )
                    yield build_sse_event(
                        {
                            "type": AssistantEventType.ERROR.mark,
                            "message": "AI 助手响应超时，请稍后重试",
                        }
                    )
                    yield build_sse_event(
                        {
                            "type": AssistantEventType.DONE.mark,
                            "conversation_id": body.conversation_id,
                            "message_id": None,
                        }
                    )
                    return

                # 2. 客户端断连：节流检测，命中则静默终止（客户端已收不到事件）
                if now - last_disconnect_check >= _DISCONNECT_CHECK_INTERVAL:
                    last_disconnect_check = now
                    if _is_client_disconnected(request):
                        logger.info(
                            f"AI 助手客户端已断开，终止对话流；"
                            f"conversation={body.conversation_id}"
                        )
                        return

                yield build_sse_event(event)
        except Exception as exc:  # noqa: BLE001 - SSE 通道最后防线，仅兜底不可预期异常
            logger.error(f"AI 助手 SSE 通道异常: {exc}")
            yield build_sse_event(
                {
                    "type": AssistantEventType.ERROR.mark,
                    "message": AssistantEventType.ERROR.desc,
                }
            )
            yield build_sse_event(
                {
                    "type": AssistantEventType.DONE.mark,
                    "conversation_id": body.conversation_id,
                    "message_id": None,
                }
            )

    return StreamingResponse(
        generate(),
        media_type=HttpContentType.TEXT_EVENT_STREAM.value,
        headers=_SSE_HEADERS,
    )


@router.post(
    "/conversations",
    summary="创建会话",
    description="创建一个新的 AI 助手会话",
)
@permission(PermissionCode.ASSISTANT_CONVERSATION)
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
    return success_response(ConversationResponse.model_validate(entity), request)


@router.get(
    "/conversations",
    summary="会话列表",
    description="查询当前用户的 AI 助手会话列表",
)
@permission(PermissionCode.ASSISTANT_CONVERSATION)
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
        [ConversationResponse.model_validate(item) for item in conversations],
        request,
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    summary="会话消息列表",
    description="查询指定会话的消息列表（校验归属）",
)
@permission(PermissionCode.ASSISTANT_CONVERSATION)
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
        [MessageResponse.model_validate(item) for item in messages],
        request,
    )


@router.delete(
    "/conversations/{conversation_id}",
    summary="删除会话",
    description="软删除指定会话（标记 deleted_at，消息与反馈保留留档；校验归属）",
)
@permission(PermissionCode.ASSISTANT_CONVERSATION)
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
@permission(PermissionCode.ASSISTANT_CONVERSATION)
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
    return success_response(ConversationResponse.model_validate(entity), request)


@router.post(
    "/feedback",
    summary="消息反馈",
    description="用户对助手回复进行 👍👎 反馈（提示词调优数据源）",
)
@permission(PermissionCode.ASSISTANT_FEEDBACK)
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
