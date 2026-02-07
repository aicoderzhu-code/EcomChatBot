"""
PostgreSQL Row Level Security (RLS) 辅助模块

提供设置和管理 RLS session 变量的工具函数。
"""
from typing import AsyncGenerator
from contextlib import asynccontextmanager
import logging

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def set_current_tenant(db: AsyncSession, tenant_id: str):
    """
    设置当前租户ID（用于 RLS 策略）

    Args:
        db: 数据库会话
        tenant_id: 租户ID

    Usage:
        await set_current_tenant(db, "xxx-xxx-xxx")
        # 之后的所有查询都会自动过滤 tenant_id
    """
    try:
        # 设置 session 变量
        await db.execute(
            f"SET LOCAL app.current_tenant_id = '{tenant_id}'"
        )
        logger.debug(f"RLS: Set current tenant to {tenant_id}")
    except Exception as e:
        logger.error(f"Failed to set current tenant: {e}")
        raise


async def set_admin_mode(db: AsyncSession, is_admin: bool = True):
    """
    设置管理员模式（用于绕过 RLS 策略）

    Args:
        db: 数据库会话
        is_admin: 是否为管理员模式

    Usage:
        await set_admin_mode(db, True)
        # 管理员可以访问所有租户的数据
    """
    try:
        value = 'true' if is_admin else 'false'
        await db.execute(
            f"SET LOCAL app.is_admin = '{value}'"
        )
        logger.debug(f"RLS: Set admin mode to {is_admin}")
    except Exception as e:
        logger.error(f"Failed to set admin mode: {e}")
        raise


async def clear_rls_context(db: AsyncSession):
    """
    清除 RLS 上下文（重置 session 变量）

    Args:
        db: 数据库会话
    """
    try:
        await db.execute("RESET app.current_tenant_id")
        await db.execute("RESET app.is_admin")
        logger.debug("RLS: Context cleared")
    except Exception as e:
        logger.warning(f"Failed to clear RLS context: {e}")


@asynccontextmanager
async def tenant_context(
    db: AsyncSession,
    tenant_id: str
) -> AsyncGenerator[AsyncSession, None]:
    """
    租户上下文管理器（自动设置和清理 RLS 上下文）

    Args:
        db: 数据库会话
        tenant_id: 租户ID

    Usage:
        async with tenant_context(db, "xxx-xxx-xxx"):
            # 在这个上下文中的所有查询都会自动过滤 tenant_id
            conversations = await db.execute(select(Conversation))
    """
    try:
        await set_current_tenant(db, tenant_id)
        yield db
    finally:
        await clear_rls_context(db)


@asynccontextmanager
async def admin_context(
    db: AsyncSession
) -> AsyncGenerator[AsyncSession, None]:
    """
    管理员上下文管理器（自动启用和清理管理员模式）

    Args:
        db: 数据库会话

    Usage:
        async with admin_context(db):
            # 在这个上下文中可以访问所有租户的数据
            all_conversations = await db.execute(select(Conversation))
    """
    try:
        await set_admin_mode(db, True)
        yield db
    finally:
        await set_admin_mode(db, False)
        await clear_rls_context(db)


# ==================== 依赖注入支持 ====================


async def apply_tenant_rls(db: AsyncSession, tenant_id: str) -> AsyncSession:
    """
    应用租户 RLS 策略（用于依赖注入）

    Usage in FastAPI:
        @router.get("/conversations")
        async def get_conversations(
            db: Annotated[AsyncSession, Depends(get_db)],
            tenant_id: TenantDep
        ):
            await apply_tenant_rls(db, tenant_id)
            # 后续查询自动过滤 tenant_id
            conversations = await db.execute(select(Conversation))
            return conversations

    Args:
        db: 数据库会话
        tenant_id: 租户ID

    Returns:
        配置了 RLS 的数据库会话
    """
    await set_current_tenant(db, tenant_id)
    return db


async def apply_admin_rls(db: AsyncSession) -> AsyncSession:
    """
    应用管理员 RLS 策略（用于依赖注入）

    Usage in FastAPI:
        @router.get("/admin/all-conversations")
        async def get_all_conversations(
            db: Annotated[AsyncSession, Depends(get_db)],
            admin: AdminDep
        ):
            await apply_admin_rls(db)
            # 可以访问所有租户的数据
            conversations = await db.execute(select(Conversation))
            return conversations

    Args:
        db: 数据库会话

    Returns:
        配置了管理员模式的数据库会话
    """
    await set_admin_mode(db, True)
    return db


# ==================== RLS 验证工具 ====================


async def verify_rls_enabled(db: AsyncSession) -> bool:
    """
    验证 RLS 是否已启用

    Args:
        db: 数据库会话

    Returns:
        是否启用了 RLS
    """
    try:
        result = await db.execute("""
            SELECT COUNT(*)
            FROM pg_tables t
            JOIN pg_class c ON c.relname = t.tablename
            WHERE t.schemaname = 'public'
            AND c.relrowsecurity = true
        """)
        count = result.scalar()
        return count > 0
    except Exception as e:
        logger.error(f"Failed to verify RLS status: {e}")
        return False


async def get_rls_status(db: AsyncSession) -> dict:
    """
    获取 RLS 状态信息

    Args:
        db: 数据库会话

    Returns:
        {
            "enabled_tables": ["table1", "table2", ...],
            "total_tables": 10,
            "current_tenant_id": "xxx-xxx-xxx",
            "is_admin": false
        }
    """
    try:
        # 获取启用 RLS 的表
        result = await db.execute("""
            SELECT t.tablename
            FROM pg_tables t
            JOIN pg_class c ON c.relname = t.tablename
            WHERE t.schemaname = 'public'
            AND c.relrowsecurity = true
            ORDER BY t.tablename
        """)
        enabled_tables = [row[0] for row in result.fetchall()]

        # 获取当前租户ID
        try:
            tenant_result = await db.execute(
                "SELECT current_setting('app.current_tenant_id', true)"
            )
            current_tenant_id = tenant_result.scalar()
        except:
            current_tenant_id = None

        # 获取管理员状态
        try:
            admin_result = await db.execute(
                "SELECT current_setting('app.is_admin', true)"
            )
            is_admin = admin_result.scalar() == 'true'
        except:
            is_admin = False

        return {
            "enabled_tables": enabled_tables,
            "total_tables": len(enabled_tables),
            "current_tenant_id": current_tenant_id,
            "is_admin": is_admin,
        }
    except Exception as e:
        logger.error(f"Failed to get RLS status: {e}")
        return {
            "enabled_tables": [],
            "total_tables": 0,
            "current_tenant_id": None,
            "is_admin": False,
            "error": str(e),
        }
