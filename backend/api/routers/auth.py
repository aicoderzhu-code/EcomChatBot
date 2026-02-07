"""
租户认证 API 路由
"""
from fastapi import APIRouter, Request, Response

from api.dependencies import DBDep, TenantTokenDep
from api.middleware import generate_csrf_token
from core import (
    InvalidTokenException,
    create_access_token,
    create_refresh_token,
    decode_token,
    settings,
)
from schemas import ApiResponse
from schemas.tenant import (
    TenantLoginRequest,
    TenantLoginResponse,
    TenantLogoutRequest,
    TenantLogoutResponse,
    TenantRegisterRequest,
    TenantRegisterResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
)
from services import TenantService

router = APIRouter(prefix="/auth", tags=["租户认证"])


@router.post("/register", response_model=ApiResponse[TenantRegisterResponse])
async def register(
    register_data: TenantRegisterRequest,
    db: DBDep,
):
    """
    租户注册

    自助注册新租户账户，默认为免费套餐
    """
    service = TenantService(db)
    tenant_id, api_key = await service.register_tenant(register_data)

    response = TenantRegisterResponse(
        tenant_id=tenant_id,
        api_key=api_key,
        message="注册成功",
    )

    return ApiResponse(data=response)


@router.post("/login", response_model=ApiResponse[TenantLoginResponse])
async def login(
    login_data: TenantLoginRequest,
    request: Request,
    db: DBDep,
):
    """
    租户登录

    使用邮箱和密码登录，返回访问 Token 和刷新 Token
    """
    # 获取客户端 IP
    client_ip = request.client.host if request.client else None

    service = TenantService(db)
    tenant = await service.authenticate_tenant(
        email=login_data.email,
        password=login_data.password,
        login_ip=client_ip,
    )

    # 生成访问 Token
    access_token = create_access_token(
        subject=tenant.tenant_id,
        tenant_id=tenant.tenant_id,
    )

    # 生成刷新 Token
    refresh_token = create_refresh_token(subject=tenant.tenant_id)

    # 存储刷新 Token 哈希
    await service.store_refresh_token(tenant.tenant_id, refresh_token)

    response = TenantLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_hours * 3600,
        tenant_id=tenant.tenant_id,
    )

    return ApiResponse(data=response)


@router.post("/refresh", response_model=ApiResponse[TokenRefreshResponse])
async def refresh_token(
    refresh_data: TokenRefreshRequest,
    db: DBDep,
):
    """
    刷新 Token

    使用刷新 Token 获取新的访问 Token
    """
    try:
        # 解码刷新 Token
        payload = decode_token(refresh_data.refresh_token)

        # 验证 Token 类型
        if payload.get("type") != "refresh":
            raise InvalidTokenException("无效的刷新 Token")

        tenant_id = payload.get("sub")
        if not tenant_id:
            raise InvalidTokenException("无效的刷新 Token")

        # 验证刷新 Token 是否有效
        service = TenantService(db)
        is_valid = await service.verify_refresh_token(
            tenant_id, refresh_data.refresh_token
        )
        if not is_valid:
            raise InvalidTokenException("刷新 Token 已失效")

        # 检查租户状态
        await service.check_tenant_access(tenant_id)

        # 生成新的访问 Token
        new_access_token = create_access_token(
            subject=tenant_id,
            tenant_id=tenant_id,
        )

        response = TokenRefreshResponse(
            access_token=new_access_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_hours * 3600,
        )

        return ApiResponse(data=response)

    except ValueError as e:
        raise InvalidTokenException(str(e))


@router.post("/logout", response_model=ApiResponse[TenantLogoutResponse])
async def logout(
    logout_data: TenantLogoutRequest,
    tenant_id: TenantTokenDep,
    db: DBDep,
):
    """
    租户登出

    使刷新 Token 失效
    """
    service = TenantService(db)

    # 使刷新 Token 失效
    await service.invalidate_refresh_token(tenant_id)

    response = TenantLogoutResponse(message="登出成功")

    return ApiResponse(data=response)


@router.get("/csrf-token")
async def get_csrf_token(
    request: Request,
    response: Response,
):
    """
    获取 CSRF Token

    用于需要 CSRF 保护的表单提交。
    Token 会同时在响应体和 Cookie 中返回。

    Returns:
        {
            "csrf_token": "token_string",
            "expires_in": 3600
        }
    """
    # 生成 CSRF Token
    csrf_token = generate_csrf_token()

    # 设置 Cookie（SameSite 和 Secure 选项）
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        max_age=3600,  # 1小时
        httponly=True,  # 防止 JavaScript 访问
        samesite="lax",  # CSRF 保护
        secure=False,  # 生产环境应设为 True (需要 HTTPS)
    )

    return ApiResponse(
        data={
            "csrf_token": csrf_token,
            "expires_in": 3600,
        }
    )
