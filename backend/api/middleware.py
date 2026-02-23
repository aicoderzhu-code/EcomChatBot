"""
API中间件
"""
from typing import Annotated, Callable
import logging
import secrets
import hashlib
import time

from fastapi import Depends, Request, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import DBDep, TenantFlexDep
from api.content_filter import ContentFilter
from core.exceptions import QuotaExceededException, ValidationException
from services import QuotaService

logger = logging.getLogger(__name__)

# CSRF Token 密钥（生产环境应从环境变量读取）
CSRF_SECRET_KEY = secrets.token_urlsafe(32)


async def check_conversation_quota(
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """
    检查对话次数配额（依赖注入）

    用于创建会话、发送消息等场景
    """
    quota_service = QuotaService(db)
    await quota_service.check_conversation_quota(tenant_id)
    return tenant_id


async def check_concurrent_quota(
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """
    检查并发会话配额（依赖注入）

    用于创建新会话时检查
    """
    from services.conversation_service import ConversationService

    quota_service = QuotaService(db)
    conversation_service = ConversationService(db, tenant_id)  # 传递tenant_id

    # 获取当前活跃会话数（不需要传递参数，服务内部会使用self.tenant_id）
    active_count = await conversation_service.get_active_conversation_count()
    await quota_service.check_concurrent_quota(tenant_id, active_count)

    return tenant_id


async def check_storage_quota(
    tenant_id: TenantFlexDep,
    db: DBDep,
    file_size: float = 0.0,
):
    """
    检查存储空间配额（依赖注入）

    用于上传文件、添加知识库等场景

    Args:
        file_size: 需要新增的文件大小(MB)，会转换为GB
    """
    quota_service = QuotaService(db)
    # 转换MB到GB
    size_gb = file_size / 1024 if file_size > 0 else 0
    await quota_service.check_storage_quota(tenant_id, size_gb)
    return tenant_id


async def check_api_quota(
    tenant_id: TenantFlexDep,
    db: DBDep,
):
    """
    检查API调用配额（依赖注入）

    用于API接口调用
    """
    quota_service = QuotaService(db)
    await quota_service.check_api_quota(tenant_id)
    return tenant_id


# 组合依赖注入（同时检查多个配额）
ConversationQuotaDep = Annotated[str, Depends(check_conversation_quota)]
ConcurrentQuotaDep = Annotated[str, Depends(check_concurrent_quota)]
StorageQuotaDep = Annotated[str, Depends(check_storage_quota)]
ApiQuotaDep = Annotated[str, Depends(check_api_quota)]


# ==================== 内容安全过滤 ====================


async def validate_user_input(request: Request) -> Request:
    """
    验证和过滤用户输入，防止XSS和注入攻击

    用于需要检查用户输入安全性的API端点
    """
    # 获取请求体
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()
        except Exception:
            # 不是JSON请求或没有body，跳过
            return request

        # 检查所有字符串字段
        issues_found = []
        for key, value in body.items():
            if isinstance(value, str):
                # 检测注入攻击
                if ContentFilter.detect_injection(value):
                    issues_found.append(f"字段 '{key}' 包含潜在的注入攻击代码")
                    logger.warning(
                        f"XSS/Injection detected in field '{key}': {value[:100]}"
                    )

                # 检测敏感词
                if ContentFilter.contains_sensitive_words(value):
                    issues_found.append(f"字段 '{key}' 包含敏感词")
                    logger.warning(f"Sensitive words detected in field '{key}'")

        # 如果发现安全问题，拒绝请求
        if issues_found:
            raise ValidationException(
                message="输入内容包含不安全的内容",
                details={"issues": issues_found},
            )

    return request


def sanitize_text_field(text: str) -> str:
    """
    清理文本字段（用于单个字段过滤）

    Args:
        text: 待过滤的文本

    Returns:
        清理后的文本
    """
    if not text:
        return text

    result = ContentFilter.sanitize_content(text)

    # 如果检测到注入攻击，抛出异常
    if "potential_injection" in result["issues"]:
        raise ValidationException(
            message="输入内容包含不安全的代码",
            details={"issues": result["issues"]},
        )

    # 如果包含敏感词，记录日志但不阻止
    if "contains_sensitive_words" in result["issues"]:
        logger.warning(f"Sensitive words found in input: {text[:100]}")

    # 返回清理后的文本
    return result["cleaned"]


# 内容安全依赖注入
SafeInputDep = Annotated[Request, Depends(validate_user_input)]


# ==================== CSRF 防护 ====================


def generate_csrf_token(session_id: str = None) -> str:
    """
    生成 CSRF Token

    Args:
        session_id: 会话ID（可选，用于绑定特定会话）

    Returns:
        CSRF Token
    """
    # 使用时间戳 + 随机字符串 + 密钥生成Token
    timestamp = str(int(time.time()))
    random_str = secrets.token_urlsafe(16)

    # 拼接数据
    data = f"{timestamp}:{random_str}"
    if session_id:
        data = f"{session_id}:{data}"

    # 生成签名
    signature = hashlib.sha256(
        f"{data}:{CSRF_SECRET_KEY}".encode()
    ).hexdigest()[:16]

    # Token格式: data.signature
    token = f"{data}.{signature}"
    return token


def verify_csrf_token(token: str, session_id: str = None, max_age: int = 3600) -> bool:
    """
    验证 CSRF Token

    Args:
        token: CSRF Token
        session_id: 会话ID（可选）
        max_age: Token最大有效期（秒），默认1小时

    Returns:
        是否有效
    """
    if not token:
        return False

    try:
        # 分割Token
        parts = token.split(".")
        if len(parts) != 2:
            return False

        data, signature = parts

        # 验证签名
        expected_signature = hashlib.sha256(
            f"{data}:{CSRF_SECRET_KEY}".encode()
        ).hexdigest()[:16]

        if signature != expected_signature:
            logger.warning("CSRF token signature mismatch")
            return False

        # 解析数据
        data_parts = data.split(":")

        # 检查session_id（如果提供）
        if session_id:
            if data_parts[0] != session_id:
                logger.warning("CSRF token session_id mismatch")
                return False
            timestamp_str = data_parts[1]
        else:
            timestamp_str = data_parts[0]

        # 检查时间戳
        timestamp = int(timestamp_str)
        current_time = int(time.time())

        if current_time - timestamp > max_age:
            logger.warning("CSRF token expired")
            return False

        return True

    except Exception as e:
        logger.error(f"CSRF token verification error: {e}")
        return False


async def verify_csrf(
    request: Request,
    x_csrf_token: Annotated[str | None, Header()] = None,
) -> bool:
    """
    CSRF Token 验证依赖注入

    用于需要CSRF保护的API端点（POST/PUT/DELETE等修改操作）

    使用示例:
        @router.post("/sensitive-operation", dependencies=[Depends(verify_csrf)])
    """
    # 只对修改操作进行CSRF检查
    if request.method in ["GET", "HEAD", "OPTIONS"]:
        return True

    # API Key 认证的请求不需要CSRF保护
    # （因为API Key本身就是一种身份验证）
    if request.headers.get("x-api-key"):
        return True

    # 检查 CSRF Token
    if not x_csrf_token:
        # 尝试从Cookie中获取
        csrf_from_cookie = request.cookies.get("csrf_token")
        if csrf_from_cookie:
            x_csrf_token = csrf_from_cookie

    if not x_csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="缺少 CSRF Token",
        )

    # 验证Token
    if not verify_csrf_token(x_csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF Token 无效或已过期",
        )

    return True


# CSRF 依赖注入
CSRFProtectedDep = Annotated[bool, Depends(verify_csrf)]
