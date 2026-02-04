"""
安全模块：JWT、API Key、密码加密
"""
import secrets
from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from core.config import settings

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """哈希密码"""
    return pwd_context.hash(password)


def create_access_token(
    subject: str,
    role: str | None = None,
    tenant_id: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    创建访问 Token
    
    Args:
        subject: 用户标识（admin_id 或 tenant_id）
        role: 角色（用于管理员）
        tenant_id: 租户 ID（用于租户 API）
        expires_delta: 过期时间增量
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            hours=settings.jwt_access_token_expire_hours
        )

    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    if role:
        payload["role"] = role
    if tenant_id:
        payload["tenant_id"] = tenant_id

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    """创建刷新 Token"""
    expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {
        "sub": subject,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """
    解码 Token
    
    Raises:
        JWTError: Token 无效或过期
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        raise ValueError(f"Token 验证失败: {str(e)}")


def generate_api_key() -> str:
    """
    生成 API Key
    
    格式: eck_<32位随机字符串>
    """
    random_part = secrets.token_urlsafe(settings.api_key_length)
    return f"{settings.api_key_prefix}{random_part}"


def hash_api_key(api_key: str) -> str:
    """哈希 API Key（用于数据库存储）"""
    return pwd_context.hash(api_key)


def verify_api_key(plain_api_key: str, hashed_api_key: str) -> bool:
    """验证 API Key"""
    return pwd_context.verify(plain_api_key, hashed_api_key)


def generate_tenant_id() -> str:
    """
    生成租户 ID
    
    格式: tenant_<timestamp>_<random>
    """
    timestamp = int(datetime.utcnow().timestamp())
    random_part = secrets.token_hex(8)
    return f"tenant_{timestamp}_{random_part}"


def generate_conversation_id() -> str:
    """
    生成会话 ID
    
    格式: conv_<timestamp>_<random>
    """
    timestamp = int(datetime.utcnow().timestamp())
    random_part = secrets.token_hex(8)
    return f"conv_{timestamp}_{random_part}"


def generate_admin_id() -> str:
    """
    生成管理员 ID
    
    格式: admin_<timestamp>_<random>
    """
    timestamp = int(datetime.utcnow().timestamp())
    random_part = secrets.token_hex(6)
    return f"admin_{timestamp}_{random_part}"
