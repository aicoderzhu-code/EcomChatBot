"""
系统初始化 API 路由

提供系统初始化状态检查和首次超级管理员创建功能。
这些端点无需认证，但仅在系统未初始化时可用。
"""
import logging

from fastapi import APIRouter, HTTPException, status

from api.dependencies import DBDep
from schemas import ApiResponse
from schemas.setup import InitialAdminCreate, SetupStatus
from services import AuditService, SetupService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/setup", tags=["系统初始化"])


@router.get("/status", response_model=ApiResponse[SetupStatus])
async def get_setup_status(db: DBDep):
    """
    检查系统初始化状态

    无需认证，用于前端判断是否需要跳转到初始化页面。

    返回:
    - initialized: 系统是否已初始化（是否存在管理员）
    - admin_count: 当前管理员数量
    """
    service = SetupService(db)
    status_data = await service.check_initialization_status()
    return ApiResponse(data=status_data)


@router.post("/init", response_model=ApiResponse[dict])
async def initialize_system(
    data: InitialAdminCreate,
    db: DBDep,
):
    """
    创建初始超级管理员

    无需认证，但仅当系统未初始化（admin_count == 0）时可用。
    创建的账户将自动成为超级管理员。

    安全限制:
    - 仅当无管理员存在时可调用
    - 已存在管理员时返回 403 Forbidden
    - 密码必须符合强度要求（至少8位，包含大小写字母和数字）
    """
    service = SetupService(db)

    # 检查系统是否已初始化
    status_data = await service.check_initialization_status()
    if status_data.initialized:
        logger.warning("尝试在已初始化的系统上创建初始管理员")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="系统已初始化，无法再次创建初始管理员"
        )

    try:
        # 创建初始超级管理员
        admin = await service.create_initial_admin(data)

        # 记录审计日志
        audit_service = AuditService(db)
        await audit_service.log_operation(
            admin_id=admin.admin_id,
            operation_type="system_init",
            resource_type="admin",
            resource_id=admin.admin_id,
            operation_details={
                "username": admin.username,
                "email": admin.email,
                "role": admin.role,
                "action": "initial_admin_created",
            },
        )

        logger.info(f"系统初始化完成，创建超级管理员: {admin.username}")

        return ApiResponse(
            data={
                "message": "系统初始化成功",
                "admin_id": admin.admin_id,
                "username": admin.username,
            }
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"系统初始化失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="系统初始化失败，请稍后重试"
        )
