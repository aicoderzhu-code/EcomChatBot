"""
账单和支付相关的后台任务
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from tasks.celery_app import celery_app
from db import get_async_session
from models.payment import PaymentOrder, OrderStatus
from models.tenant import Subscription
from services.billing_service import BillingService
from services.subscription_service import SubscriptionService, ServiceDegradationManager
from services.quota_service import QuotaService

logger = logging.getLogger(__name__)


@celery_app.task
async def generate_monthly_bills(month: str) -> Dict[str, Any]:
    """
    生成月度账单

    Args:
        month: 月份 (格式: YYYY-MM)

    Returns:
        生成结果
    """
    try:
        logger.info(f"生成月度账单: month={month}")

        # 解析月份
        year, mon = map(int, month.split('-'))
        start_date = datetime(year, mon, 1)
        if mon == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end_date = datetime(year, mon + 1, 1) - timedelta(seconds=1)

        async with get_async_session() as db:
            billing_service = BillingService(db)

            # 1. 查询所有活跃订阅
            stmt = select(Subscription).where(
                and_(
                    Subscription.status == "active",
                    Subscription.created_at <= end_date
                )
            )
            result = await db.execute(stmt)
            subscriptions = result.scalars().all()

            generated_bills = 0
            total_amount = 0.0
            failed_count = 0

            # 2. 为每个订阅生成账单
            for subscription in subscriptions:
                try:
                    # 统计月度用量
                    from models.conversation import Conversation, Message
                    from sqlalchemy import func

                    # 统计对话数
                    conv_stmt = select(func.count(Conversation.id)).where(
                        and_(
                            Conversation.tenant_id == subscription.tenant_id,
                            Conversation.created_at >= start_date,
                            Conversation.created_at <= end_date
                        )
                    )
                    conv_result = await db.execute(conv_stmt)
                    conversation_count = conv_result.scalar() or 0

                    # 统计Token消耗
                    token_stmt = select(
                        func.sum(Message.input_tokens) + func.sum(Message.output_tokens)
                    ).join(Conversation).where(
                        and_(
                            Conversation.tenant_id == subscription.tenant_id,
                            Message.created_at >= start_date,
                            Message.created_at <= end_date
                        )
                    )
                    token_result = await db.execute(token_stmt)
                    token_usage = token_result.scalar() or 0

                    # 计算超额费用
                    usage_data = {
                        "conversation_count": conversation_count,
                        "token_usage": token_usage,
                    }

                    # 创建账单
                    bill = await billing_service.create_bill(
                        tenant_id=subscription.tenant_id,
                        bill_type="subscription",
                        billing_period=month,
                        usage_data=usage_data
                    )

                    generated_bills += 1
                    total_amount += float(bill.total_amount)

                    logger.info(f"生成账单成功: tenant={subscription.tenant_id}, amount={bill.total_amount}")

                except Exception as e:
                    logger.error(f"生成账单失败 (tenant={subscription.tenant_id}): {e}")
                    failed_count += 1

            return {
                "success": True,
                "generated_bills": generated_bills,
                "failed_bills": failed_count,
                "total_amount": round(total_amount, 2),
                "message": f"月度账单生成完成，成功{generated_bills}个，失败{failed_count}个",
            }

    except Exception as e:
        logger.error(f"月度账单生成失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@celery_app.task
async def sync_pending_orders() -> Dict[str, Any]:
    """
    同步待处理订单状态

    查询待支付订单(状态=PENDING, 创建超过5分钟, 未过期),
    根据支付渠道查询支付平台的订单状态,更新本地订单。

    Returns:
        同步结果统计
    """
    try:
        logger.info("开始同步待处理订单状态")

        async with get_async_session() as db:
            now = datetime.utcnow()
            five_minutes_ago = now - timedelta(minutes=5)

            # 1. 查询待支付订单(创建超过5分钟,未过期)
            stmt = select(PaymentOrder).where(
                and_(
                    PaymentOrder.status == OrderStatus.PENDING,
                    PaymentOrder.created_at <= five_minutes_ago,
                    PaymentOrder.expired_at > now
                )
            )
            result = await db.execute(stmt)
            pending_orders = result.scalars().all()

            # 2. 查询已过期但仍为PENDING状态的订单
            expired_stmt = select(PaymentOrder).where(
                and_(
                    PaymentOrder.status == OrderStatus.PENDING,
                    PaymentOrder.expired_at <= now
                )
            )
            expired_result = await db.execute(expired_stmt)
            expired_orders = expired_result.scalars().all()

            stats = {
                "synced_orders": 0,
                "paid_orders": 0,
                "closed_orders": 0,
                "expired_orders": 0,
                "errors": 0
            }

            # 3. 处理待支付订单
            from services.alipay_client import get_alipay_client
            from services.wechat_pay import WechatPayClient, WechatPayConfig
            from services.payment_service import PaymentService
            from models.payment import PaymentChannel

            alipay_client = get_alipay_client()
            payment_service = PaymentService(db)

            for order in pending_orders:
                try:
                    trade_status = None
                    trade_no = None

                    if order.payment_channel == PaymentChannel.ALIPAY:
                        # 查询支付宝订单状态
                        query_result = alipay_client.query_order(
                            order_number=order.order_number
                        )
                        if query_result:
                            trade_status = query_result.get("trade_status")
                            trade_no = query_result.get("trade_no")

                    elif order.payment_channel == PaymentChannel.WECHAT:
                        # 查询微信订单状态
                        if payment_service.wechat_client:
                            query_result = await payment_service.wechat_client.query_order(
                                order.order_number
                            )
                            if query_result:
                                trade_status = query_result.get("trade_state")
                                trade_no = query_result.get("transaction_id")

                    # 根据查询结果更新订单
                    if trade_status in ["TRADE_SUCCESS", "SUCCESS"]:
                        # 支付成功
                        order.status = OrderStatus.PAID
                        order.trade_no = trade_no
                        order.paid_at = datetime.utcnow()

                        # 激活订阅
                        await payment_service._activate_subscription(order)

                        stats["paid_orders"] += 1
                        logger.info(f"订单同步-支付成功: {order.order_number}")

                    elif trade_status in ["TRADE_CLOSED", "CLOSED"]:
                        # 订单已关闭
                        order.status = OrderStatus.CANCELLED
                        stats["closed_orders"] += 1
                        logger.info(f"订单同步-已关闭: {order.order_number}")

                    stats["synced_orders"] += 1

                except Exception as e:
                    logger.error(f"同步订单失败 ({order.order_number}): {e}")
                    stats["errors"] += 1

            # 4. 处理过期订单
            for order in expired_orders:
                try:
                    order.status = OrderStatus.EXPIRED
                    stats["expired_orders"] += 1
                    logger.info(f"订单已过期: {order.order_number}")
                except Exception as e:
                    logger.error(f"处理过期订单失败 ({order.order_number}): {e}")
                    stats["errors"] += 1

            await db.commit()

            logger.info(
                f"订单同步完成: 共同步{stats['synced_orders']}个, "
                f"支付成功{stats['paid_orders']}个, "
                f"已关闭{stats['closed_orders']}个, "
                f"已过期{stats['expired_orders']}个, "
                f"失败{stats['errors']}个"
            )

            return {
                "success": True,
                **stats,
                "message": "订单状态同步完成",
            }

    except Exception as e:
        logger.error(f"订单状态同步失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@celery_app.task
async def process_subscription_renewal(tenant_id: str = None) -> Dict[str, Any]:
    """
    处理订阅续费(定时任务)

    扫描即将到期的订阅(3天内),尝试自动续费

    Args:
        tenant_id: 租户ID(可选,不传则处理所有即将到期的订阅)

    Returns:
        处理结果
    """
    try:
        logger.info(f"开始处理订阅续费, tenant_id={tenant_id}")

        async with get_async_session() as db:
            now = datetime.utcnow()
            three_days_later = now + timedelta(days=3)

            # 查询即将到期且开启自动续费的订阅
            query = select(Subscription).where(
                and_(
                    Subscription.status == "active",
                    Subscription.auto_renew == True,
                    Subscription.expire_at > now,
                    Subscription.expire_at <= three_days_later
                )
            )

            if tenant_id:
                query = query.where(Subscription.tenant_id == tenant_id)

            result = await db.execute(query)
            subscriptions = result.scalars().all()

            success_count = 0
            failed_count = 0
            skipped_count = 0

            for subscription in subscriptions:
                try:
                    result = await process_single_renewal(db, subscription)
                    if result["success"]:
                        success_count += 1
                    elif result.get("skipped"):
                        skipped_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
                    logger.error(f"续费失败 (tenant={subscription.tenant_id}): {e}")

            return {
                "success": True,
                "total": len(subscriptions),
                "success_count": success_count,
                "failed_count": failed_count,
                "skipped_count": skipped_count,
                "message": f"续费处理完成: 成功{success_count}, 失败{failed_count}, 跳过{skipped_count}"
            }

    except Exception as e:
        logger.error(f"订阅续费任务失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


async def process_single_renewal(db: AsyncSession, subscription: Subscription) -> Dict[str, Any]:
    """
    处理单个订阅的续费

    Args:
        db: 数据库会话
        subscription: 订阅对象

    Returns:
        处理结果
    """
    tenant_id = subscription.tenant_id
    logger.info(f"处理订阅续费: tenant={tenant_id}, plan={subscription.plan_type}")

    # 1. 检查是否有未支付的账单
    from models.payment import PaymentOrder, OrderStatus

    pending_bills_stmt = select(PaymentOrder).where(
        and_(
            PaymentOrder.tenant_id == tenant_id,
            PaymentOrder.status.in_([OrderStatus.PENDING, OrderStatus.FAILED])
        )
    )
    pending_result = await db.execute(pending_bills_stmt)
    pending_bills = pending_result.scalars().all()

    if pending_bills:
        logger.warning(f"租户 {tenant_id} 有 {len(pending_bills)} 个未支付订单,跳过自动续费")
        # 发送提醒通知
        await send_renewal_reminder_notification(tenant_id, "pending_bills")
        return {"success": False, "skipped": True, "reason": "有未支付订单"}

    # 2. 获取租户信息
    from models.tenant import Tenant

    tenant_stmt = select(Tenant).where(Tenant.tenant_id == tenant_id)
    tenant_result = await db.execute(tenant_stmt)
    tenant = tenant_result.scalar_one_or_none()

    if not tenant:
        logger.error(f"租户不存在: {tenant_id}")
        return {"success": False, "reason": "租户不存在"}

    # 3. 计算续费金额
    from services.payment_service import PaymentService, PLAN_PRICES

    # 默认续费1个月(可以从配置中读取)
    duration_months = 1
    plan_price = PLAN_PRICES.get(subscription.plan_type)

    if not plan_price:
        logger.error(f"无效的套餐类型: {subscription.plan_type}")
        return {"success": False, "reason": "无效的套餐类型"}

    total_amount = plan_price * duration_months

    # 4. 尝试自动扣款
    payment_service = PaymentService(db)

    # 检查租户是否设置了默认支付方式
    # TODO: 需要在Tenant模型中添加 default_payment_channel 字段
    # 这里暂时使用支付宝
    payment_channel = "alipay"  # 或从 tenant.default_payment_channel 获取

    try:
        # 创建续费订单
        from models.payment import PaymentType, SubscriptionType

        if payment_channel == "wechat":
            # 微信支付续费(需要用户主动扫码,不能自动扣款)
            # 发送续费提醒,引导用户支付
            await send_renewal_reminder_notification(tenant_id, "wechat_renewal_required")
            return {"success": False, "skipped": True, "reason": "微信支付需要用户主动扫码"}
        else:
            # 支付宝支付
            order, payment_html = await payment_service.create_payment_order(
                tenant_id=tenant.id,
                plan_type=subscription.plan_type,
                duration_months=duration_months,
                payment_type=PaymentType.PC,
                subscription_type=SubscriptionType.RENEWAL,
                description=f"{subscription.plan_type}套餐自动续费"
            )

            # 发送续费订单通知,引导用户完成支付
            await send_renewal_order_notification(tenant_id, order.order_number, float(total_amount))

            logger.info(f"创建续费订单成功: tenant={tenant_id}, order={order.order_number}")

            return {
                "success": True,
                "order_number": order.order_number,
                "amount": float(total_amount),
                "message": "已创建续费订单,等待支付"
            }

    except Exception as e:
        logger.error(f"创建续费订单失败: {e}")
        # 发送续费失败通知
        await send_renewal_failed_notification(tenant_id, str(e))
        return {"success": False, "reason": str(e)}


async def send_renewal_reminder_notification(tenant_id: str, reason: str):
    """
    发送续费提醒通知

    Args:
        tenant_id: 租户ID
        reason: 提醒原因
    """
    try:
        # TODO: 集成邮件/短信/站内信通知
        logger.info(f"发送续费提醒: tenant={tenant_id}, reason={reason}")

        # 示例: 发送邮件
        # from tasks.notification_tasks import send_email
        # send_email.delay(
        #     to=tenant.contact_email,
        #     subject="订阅即将到期提醒",
        #     body=f"您的{subscription.plan_type}套餐即将到期,请及时续费"
        # )

    except Exception as e:
        logger.error(f"发送续费提醒失败: {e}")


async def send_renewal_order_notification(tenant_id: str, order_number: str, amount: float):
    """
    发送续费订单通知

    Args:
        tenant_id: 租户ID
        order_number: 订单号
        amount: 订单金额
    """
    try:
        logger.info(f"发送续费订单通知: tenant={tenant_id}, order={order_number}, amount={amount}")

        # TODO: 发送邮件通知,包含支付链接
        # payment_url = f"https://your-domain.com/payment/orders/{order_number}"
        # send_email.delay(
        #     to=tenant.contact_email,
        #     subject="订阅续费订单",
        #     body=f"您的续费订单已创建,订单号: {order_number}, 金额: ¥{amount}, 请点击链接完成支付: {payment_url}"
        # )

    except Exception as e:
        logger.error(f"发送续费订单通知失败: {e}")


async def send_renewal_failed_notification(tenant_id: str, error: str):
    """
    发送续费失败通知

    Args:
        tenant_id: 租户ID
        error: 错误信息
    """
    try:
        logger.error(f"续费失败: tenant={tenant_id}, error={error}")

        # TODO: 发送告警通知
        # send_email.delay(
        #     to=tenant.contact_email,
        #     subject="订阅续费失败",
        #     body=f"您的订阅自动续费失败,原因: {error}, 请联系客服处理"
        # )

    except Exception as e:
        logger.error(f"发送续费失败通知失败: {e}")


@celery_app.task
async def check_expiring_subscriptions() -> Dict[str, Any]:
    """
    检查即将过期的订阅

    Returns:
        检查结果
    """
    try:
        logger.info("检查即将过期的订阅")

        async with get_async_session() as db:
            subscription_service = SubscriptionService(db)

            now = datetime.utcnow()
            seven_days_later = now + timedelta(days=7)

            # 1. 查询7天内过期的订阅
            expiring_stmt = select(Subscription).where(
                and_(
                    Subscription.status == "active",
                    Subscription.expire_at > now,
                    Subscription.expire_at <= seven_days_later
                )
            )
            expiring_result = await db.execute(expiring_stmt)
            expiring_subscriptions = expiring_result.scalars().all()

            expiring_count = len(expiring_subscriptions)

            # 分级发送续费提醒(7天、3天、1天)
            for sub in expiring_subscriptions:
                try:
                    days_left = (sub.expire_at - now).days
                    if days_left in [7, 3, 1]:
                        await send_expiring_notification(sub.tenant_id, days_left, sub)
                        logger.info(f"发送续费提醒: tenant={sub.tenant_id}, days_left={days_left}")
                except Exception as e:
                    logger.error(f"发送续费提醒失败: {e}")

            # 2. 查询已过期的订阅
            expired_stmt = select(Subscription).where(
                and_(
                    Subscription.status == "active",
                    Subscription.expire_at <= now
                )
            )
            expired_result = await db.execute(expired_stmt)
            expired_subscriptions = expired_result.scalars().all()

            expired_count = len(expired_subscriptions)

            # 处理已过期的订阅
            for sub in expired_subscriptions:
                try:
                    await handle_subscription_expired(db, sub)
                    logger.info(f"订阅已过期并处理: tenant={sub.tenant_id}")
                except Exception as e:
                    logger.error(f"处理过期订阅失败: {e}")

            await db.commit()

            return {
                "success": True,
                "expiring_soon": expiring_count,
                "expired": expired_count,
                "message": f"订阅检查完成，即将过期{expiring_count}个，已过期{expired_count}个",
            }

    except Exception as e:
        logger.error(f"订阅检查失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@celery_app.task
async def calculate_usage_charges(tenant_id: str, date: str) -> Dict[str, Any]:
    """
    计算用量费用

    Args:
        tenant_id: 租户ID
        date: 日期 (格式: YYYY-MM-DD)

    Returns:
        计算结果
    """
    try:
        logger.info(f"计算用量费用: tenant={tenant_id}, date={date}")

        # 解析日期
        year, mon, day = map(int, date.split('-'))
        start_date = datetime(year, mon, day)
        end_date = start_date + timedelta(days=1) - timedelta(seconds=1)

        async with get_async_session() as db:
            quota_service = QuotaService(db)

            # 1. 统计当日用量
            from models.conversation import Conversation, Message
            from sqlalchemy import func

            # 统计对话数
            conv_stmt = select(func.count(Conversation.id)).where(
                and_(
                    Conversation.tenant_id == tenant_id,
                    Conversation.created_at >= start_date,
                    Conversation.created_at <= end_date
                )
            )
            conv_result = await db.execute(conv_stmt)
            conversation_count = conv_result.scalar() or 0

            # 统计Token消耗
            token_stmt = select(
                func.sum(Message.input_tokens) + func.sum(Message.output_tokens)
            ).join(Conversation).where(
                and_(
                    Conversation.tenant_id == tenant_id,
                    Message.created_at >= start_date,
                    Message.created_at <= end_date
                )
            )
            token_result = await db.execute(token_stmt)
            token_usage = token_result.scalar() or 0

            # 2. 检查套餐配额
            subscription = await quota_service._get_subscription(tenant_id)

            # 计算超额
            quota_overage = {}
            charges = 0.0

            # 超额对话计费
            if subscription.conversation_quota and conversation_count > subscription.conversation_quota:
                overage = conversation_count - subscription.conversation_quota
                # 假设每超额1000次对话收费1元
                charge = (overage / 1000) * 1.0
                charges += charge
                quota_overage["conversation"] = {
                    "used": conversation_count,
                    "quota": subscription.conversation_quota,
                    "overage": overage,
                    "charge": round(charge, 2)
                }

            # 超额Token计费
            if subscription.api_quota and token_usage > subscription.api_quota:
                overage = token_usage - subscription.api_quota
                # 假设每超额100万Token收费10元
                charge = (overage / 1000000) * 10.0
                charges += charge
                quota_overage["api"] = {
                    "used": token_usage,
                    "quota": subscription.api_quota,
                    "overage": overage,
                    "charge": round(charge, 2)
                }

            # 3. 记录超额费用
            if charges > 0:
                # TODO: 创建超额使用记录
                logger.info(f"租户{tenant_id}在{date}超额费用: {charges}元")

            return {
                "success": True,
                "tenant_id": tenant_id,
                "date": date,
                "charges": round(charges, 2),
                "usage": {
                    "conversations": conversation_count,
                    "tokens": token_usage,
                },
                "overage": quota_overage,
                "message": "用量费用计算完成",
            }

    except Exception as e:
        logger.error(f"用量费用计算失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@celery_app.task(bind=True, max_retries=3)
async def process_refund(self, order_id: str, refund_amount: float, reason: str) -> Dict[str, Any]:
    """
    处理退款

    Args:
        order_id: 订单ID或订单号
        refund_amount: 退款金额
        reason: 退款原因

    Returns:
        退款结果
    """
    try:
        logger.info(f"处理退款: order={order_id}, amount={refund_amount}, reason={reason}")

        async with get_async_session() as db:
            from decimal import Decimal
            from services.payment_service import PaymentService
            from models.payment import PaymentChannel

            # 1. 查询订单(支持订单ID和订单号)
            if order_id.isdigit():
                stmt = select(PaymentOrder).where(PaymentOrder.id == int(order_id))
            else:
                stmt = select(PaymentOrder).where(PaymentOrder.order_number == order_id)

            result = await db.execute(stmt)
            order = result.scalar_one_or_none()

            if not order:
                logger.error(f"订单不存在: {order_id}")
                return {
                    "success": False,
                    "error": f"订单不存在: {order_id}",
                }

            # 2. 验证订单状态
            if order.status != OrderStatus.PAID:
                logger.error(f"订单状态不正确,无法退款: {order.status}")
                return {
                    "success": False,
                    "error": f"订单状态({order.status.value})不正确,只有已支付订单可退款",
                }

            # 3. 验证退款金额
            refund_decimal = Decimal(str(refund_amount))
            if refund_decimal > order.amount:
                logger.error(f"退款金额({refund_amount})超过订单金额({order.amount})")
                return {
                    "success": False,
                    "error": f"退款金额不能超过订单金额",
                }

            # 4. 根据支付渠道调用退款接口
            payment_service = PaymentService(db)
            refund_result = None

            try:
                if order.payment_channel == PaymentChannel.ALIPAY:
                    # 支付宝退款
                    refund_result = await payment_service.refund_order(
                        order_number=order.order_number,
                        refund_amount=refund_decimal,
                        refund_reason=reason
                    )
                elif order.payment_channel == PaymentChannel.WECHAT:
                    # 微信退款
                    refund_result = await payment_service.refund_wechat_order(
                        order_number=order.order_number,
                        refund_amount=refund_decimal,
                        refund_reason=reason
                    )
                else:
                    return {
                        "success": False,
                        "error": f"不支持的支付渠道: {order.payment_channel}",
                    }

            except Exception as e:
                logger.error(f"调用退款接口失败: {e}")
                raise

            # 5. 发送退款通知
            await send_refund_notification(
                tenant_id=str(order.tenant_id),
                order_number=order.order_number,
                refund_amount=float(refund_decimal),
                reason=reason
            )

            logger.info(f"退款处理成功: order={order.order_number}, amount={refund_amount}")

            return {
                "success": True,
                "order_id": order_id,
                "order_number": order.order_number,
                "refund_amount": float(refund_decimal),
                "message": "退款处理成功",
            }

    except Exception as e:
        logger.error(f"退款处理失败: {e}")
        # 可重试的错误
        raise self.retry(exc=e, countdown=60)


async def send_refund_notification(
    tenant_id: str,
    order_number: str,
    refund_amount: float,
    reason: str
):
    """
    发送退款通知

    Args:
        tenant_id: 租户ID
        order_number: 订单号
        refund_amount: 退款金额
        reason: 退款原因
    """
    try:
        logger.info(f"发送退款通知: tenant={tenant_id}, order={order_number}")

        # 调用通知任务
        from tasks.notification_tasks import send_email_notification

        # 获取租户联系邮箱
        async with get_async_session() as db:
            from models.tenant import Tenant

            stmt = select(Tenant).where(Tenant.id == int(tenant_id))
            result = await db.execute(stmt)
            tenant = result.scalar_one_or_none()

            if tenant and tenant.contact_email:
                send_email_notification.delay(
                    recipient=tenant.contact_email,
                    subject="退款成功通知",
                    content=f"""
                    <h2>退款成功</h2>
                    <p>尊敬的用户，您好！</p>
                    <p>您的订单 <strong>{order_number}</strong> 退款已处理成功。</p>
                    <ul>
                        <li>退款金额：¥{refund_amount:.2f}</li>
                        <li>退款原因：{reason}</li>
                    </ul>
                    <p>退款将在1-7个工作日内原路返回至您的支付账户。</p>
                    <p>如有疑问，请联系客服。</p>
                    """
                )

    except Exception as e:
        logger.error(f"发送退款通知失败: {e}")


@celery_app.task
async def send_invoice(bill_id: str, recipient_email: str, title_id: int = None) -> Dict[str, Any]:
    """
    发送发票

    Args:
        bill_id: 账单ID
        recipient_email: 收件人邮箱
        title_id: 发票抬头ID（可选）

    Returns:
        发送结果
    """
    try:
        logger.info(f"发送发票: bill={bill_id}, email={recipient_email}")

        async with get_async_session() as db:
            from services.invoice_service import InvoiceService
            from models.invoice import Invoice

            invoice_service = InvoiceService(db)

            # 1. 检查是否已有该账单的发票
            from sqlalchemy import select
            stmt = select(Invoice).where(Invoice.bill_id == int(bill_id))
            result = await db.execute(stmt)
            invoice = result.scalar_one_or_none()

            if not invoice:
                # 2. 创建发票
                invoice = await invoice_service.create_invoice_from_bill(
                    bill_id=int(bill_id),
                    title_id=title_id,
                    recipient_email=recipient_email,
                )
                logger.info(f"创建发票成功: invoice_number={invoice.invoice_number}")

            # 3. 开具发票（生成PDF）
            if invoice.status.value == "pending":
                invoice = await invoice_service.issue_invoice(invoice.id)
                logger.info(f"开具发票成功: invoice_number={invoice.invoice_number}")

            # 4. 发送发票
            send_result = await invoice_service.send_invoice(
                invoice_id=invoice.id,
                recipient_email=recipient_email,
            )

            if send_result["success"]:
                logger.info(f"发票发送成功: invoice={invoice.invoice_number}, email={recipient_email}")
                return {
                    "success": True,
                    "bill_id": bill_id,
                    "invoice_number": invoice.invoice_number,
                    "recipient_email": recipient_email,
                    "message": "发票发送成功",
                }
            else:
                logger.error(f"发票发送失败: {send_result.get('error')}")
                return {
                    "success": False,
                    "bill_id": bill_id,
                    "invoice_number": invoice.invoice_number,
                    "error": send_result.get("error"),
                }

    except Exception as e:
        logger.error(f"发票发送失败: {e}")
        return {
            "success": False,
            "bill_id": bill_id,
            "error": str(e),
        }


# ===== 辅助函数 =====

async def send_expiring_notification(tenant_id: str, days_left: int, subscription: Subscription):
    """
    发送订阅到期提醒

    Args:
        tenant_id: 租户ID
        days_left: 剩余天数
        subscription: 订阅对象
    """
    try:
        logger.info(f"发送到期提醒: tenant={tenant_id}, days_left={days_left}")

        # 根据剩余天数选择不同的通知模板
        if days_left == 7:
            subject = "订阅即将在7天后到期"
            urgency = "中等"
        elif days_left == 3:
            subject = "订阅即将在3天后到期"
            urgency = "紧急"
        elif days_left == 1:
            subject = "订阅即将在1天后到期"
            urgency = "非常紧急"
        else:
            subject = f"订阅即将在{days_left}天后到期"
            urgency = "提醒"

        # TODO: 发送多渠道通知
        # 1. 邮件通知
        # from tasks.notification_tasks import send_email
        # send_email.delay(
        #     to=tenant.contact_email,
        #     subject=subject,
        #     template="subscription_expiring",
        #     context={
        #         "tenant_id": tenant_id,
        #         "plan_type": subscription.plan_type,
        #         "expire_at": subscription.expire_at,
        #         "days_left": days_left,
        #         "urgency": urgency,
        #         "renewal_url": f"https://your-domain.com/billing/renew"
        #     }
        # )

        # 2. 站内通知
        # from tasks.notification_tasks import send_in_app_notification
        # send_in_app_notification.delay(
        #     tenant_id=tenant_id,
        #     title=subject,
        #     content=f"您的{subscription.plan_type}套餐将在{days_left}天后到期,请及时续费",
        #     urgency=urgency
        # )

        # 3. 短信通知(仅1天时发送)
        # if days_left == 1:
        #     from tasks.notification_tasks import send_sms
        #     send_sms.delay(
        #         phone=tenant.contact_phone,
        #         template="subscription_expiring_urgent",
        #         params={"plan": subscription.plan_type, "days": days_left}
        #     )

        logger.info(f"到期提醒已发送: tenant={tenant_id}, days={days_left}")

    except Exception as e:
        logger.error(f"发送到期提醒失败: {e}")


async def handle_subscription_expired(db: AsyncSession, subscription: Subscription):
    """
    处理过期订阅

    Args:
        db: 数据库会话
        subscription: 订阅对象
    """
    tenant_id = subscription.tenant_id
    logger.info(f"处理过期订阅: tenant={tenant_id}, plan={subscription.plan_type}")

    try:
        # 1. 更新订阅状态
        subscription.status = "expired"

        # 2. 保存当前套餐到历史(用于恢复)
        subscription.previous_plan = subscription.plan_type

        # 3. 降级到免费套餐
        subscription.plan_type = "free"

        # 4. 更新配额(使用免费套餐配额)
        from core.permissions import PLAN_CONFIGS
        free_config = PLAN_CONFIGS.get("free")

        if free_config:
            subscription.conversation_quota = free_config.get("conversation_quota", 100)
            subscription.concurrent_quota = free_config.get("concurrent_quota", 1)
            subscription.storage_quota = free_config.get("storage_quota", 100)
            subscription.api_quota = free_config.get("api_quota", 1000)

        # 5. 记录过期时间
        subscription.expired_at = datetime.utcnow()

        await db.commit()

        # 6. 发送过期通知
        await send_subscription_expired_notification(tenant_id, subscription)

        # 7. 触发Webhook事件
        # from tasks.webhook_tasks import publish_webhook_event
        # publish_webhook_event.delay(
        #     tenant_id=tenant_id,
        #     event_type="subscription.expired",
        #     data={
        #         "previous_plan": subscription.previous_plan,
        #         "current_plan": "free",
        #         "expired_at": subscription.expired_at.isoformat()
        #     }
        # )

        logger.info(f"订阅已过期并降级: tenant={tenant_id}, {subscription.previous_plan} -> free")

    except Exception as e:
        logger.error(f"处理过期订阅失败: {e}")
        await db.rollback()
        raise


async def send_subscription_expired_notification(tenant_id: str, subscription: Subscription):
    """
    发送订阅过期通知

    Args:
        tenant_id: 租户ID
        subscription: 订阅对象
    """
    try:
        logger.info(f"发送过期通知: tenant={tenant_id}")

        # TODO: 发送多渠道通知
        # 1. 邮件通知
        # send_email.delay(
        #     to=tenant.contact_email,
        #     subject="订阅已过期,已自动降级为免费套餐",
        #     template="subscription_expired",
        #     context={
        #         "tenant_id": tenant_id,
        #         "previous_plan": subscription.previous_plan,
        #         "current_plan": "free",
        #         "expired_at": subscription.expired_at,
        #         "renewal_url": "https://your-domain.com/billing/renew"
        #     }
        # )

        # 2. 站内通知
        # send_in_app_notification.delay(
        #     tenant_id=tenant_id,
        #     title="订阅已过期",
        #     content=f"您的{subscription.previous_plan}套餐已过期,账户已降级为免费套餐",
        #     urgency="urgent"
        # )

        # 3. 短信通知
        # send_sms.delay(
        #     phone=tenant.contact_phone,
        #     template="subscription_expired",
        #     params={"plan": subscription.previous_plan}
        # )

        logger.info(f"过期通知已发送: tenant={tenant_id}")

    except Exception as e:
        logger.error(f"发送过期通知失败: {e}")


@celery_app.task
async def check_service_degradation() -> Dict[str, Any]:
    """
    检查服务降级

    每天执行一次,检查所有租户的欠费状态并执行降级

    Returns:
        检查结果
    """
    try:
        logger.info("开始检查服务降级")

        async with get_async_session() as db:
            from db import get_redis
            redis = await get_redis()

            degradation_manager = ServiceDegradationManager(db, redis)

            # 批量检查所有租户
            result = await degradation_manager.batch_check_degradation()

            logger.info(
                f"服务降级检查完成: "
                f"总计{result['total']}个租户, "
                f"降级{result['degraded']}个, "
                f"恢复{result['restored']}个, "
                f"失败{result['errors']}个"
            )

            return result

    except Exception as e:
        logger.error(f"服务降级检查失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@celery_app.task
async def check_single_tenant_degradation(tenant_id: str) -> Dict[str, Any]:
    """
    检查单个租户的服务降级

    Args:
        tenant_id: 租户ID

    Returns:
        检查结果
    """
    try:
        logger.info(f"检查租户降级: tenant={tenant_id}")

        async with get_async_session() as db:
            from db import get_redis
            redis = await get_redis()

            degradation_manager = ServiceDegradationManager(db, redis)

            # 检查并执行降级
            result = await degradation_manager.check_and_degrade(tenant_id)

            if result["success"]:
                logger.info(
                    f"租户降级检查完成: tenant={tenant_id}, "
                    f"action={result['action']}, level={result.get('level')}"
                )
            else:
                logger.error(f"租户降级检查失败: tenant={tenant_id}, error={result.get('error')}")

            return result

    except Exception as e:
        logger.error(f"租户降级检查失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@celery_app.task
async def reset_monthly_quotas() -> Dict[str, Any]:
    """
    重置月度配额(每月1号凌晨0点)

    重置所有租户的对话次数和API调用配额

    Returns:
        重置结果
    """
    try:
        logger.info("开始重置月度配额")

        async with get_async_session() as db:
            from db import get_redis
            from models.tenant import Tenant

            redis = await get_redis()

            # 获取所有活跃租户
            stmt = select(Tenant).where(Tenant.status.in_(["active", "suspended"]))
            result = await db.execute(stmt)
            tenants = result.scalars().all()

            reset_count = 0
            failed_count = 0

            for tenant in tenants:
                try:
                    # 删除Redis中的配额记录
                    # 配额键格式: quota:{tenant_id}:{quota_type}:{period}
                    tenant_id = tenant.tenant_id

                    # 获取所有相关配额键
                    keys_pattern_conversation = f"quota:{tenant_id}:conversation:*"
                    keys_pattern_api = f"quota:{tenant_id}:api_call:*"

                    # 删除上月配额记录
                    async for key in redis.scan_iter(match=keys_pattern_conversation):
                        await redis.delete(key)

                    async for key in redis.scan_iter(match=keys_pattern_api):
                        await redis.delete(key)

                    reset_count += 1
                    logger.info(f"已重置租户配额: {tenant_id}")

                except Exception as e:
                    logger.error(f"重置租户配额失败 (tenant={tenant.tenant_id}): {e}")
                    failed_count += 1

            return {
                "success": True,
                "reset_count": reset_count,
                "failed_count": failed_count,
                "total_tenants": len(tenants),
                "message": f"月度配额重置完成: 成功{reset_count}个, 失败{failed_count}个"
            }

    except Exception as e:
        logger.error(f"月度配额重置失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }
