"""
数据库会话管理
"""
from collections.abc import AsyncGenerator
from contextlib import contextmanager
from typing import Any, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from core.config import settings

# 创建异步引擎
engine = create_async_engine(
    settings.database_url_str,
    echo=settings.database_echo,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
    poolclass=NullPool if settings.environment == "test" else None,
)

# 创建会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 创建基类
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话（依赖注入）
    
    用法:
        @router.get("/items")
        async def get_items(db: Annotated[AsyncSession, Depends(get_db)]):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """初始化数据库（创建所有表）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """关闭数据库连接"""
    await engine.dispose()


def get_async_session():
    """
    获取异步会话（用于Celery等非Web场景）

    Returns:
        AsyncSessionLocal上下文管理器

    用法:
        async with get_async_session() as db:
            result = await db.execute(stmt)
    """
    return AsyncSessionLocal()


# ============ 同步会话（用于 Celery 任务） ============

# 将异步数据库 URL 转换为同步 URL
_sync_database_url = settings.database_url_str.replace(
    "postgresql+asyncpg://", "postgresql://"
).replace(
    "mysql+aiomysql://", "mysql+pymysql://"
)

# 创建同步引擎
sync_engine = create_engine(
    _sync_database_url,
    echo=settings.database_echo,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
)

# 创建同步会话工厂
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """
    获取同步数据库会话（用于 Celery 任务）

    用法:
        with get_sync_session() as db:
            db.query(...)
    """
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
