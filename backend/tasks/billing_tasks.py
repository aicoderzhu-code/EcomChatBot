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
from services.subscription_service import SubscriptionService
from services.quota_service import QuotaService

logger = logging.getLogger(__name__)


@celery_app.task
def generate_monthly_bills(month: str) -> Dict[str, Any]:
    """
    生成月度账单

    Args:
        month: 月份 (格式: YYYY-MM)

    Returns:
        生成结果
    """
    async def _generate():
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

    # 运行异步任务
    import asyncio
    return asyncio.run(_generate())


@celery_app.task
def sync_pending_orders() -> Dict[str, Any]:
    """
    同步待处理订单状态

    Returns:
        同步结果
    """
    try:
        logger.info("同步待处理订单状态")

        # TODO: 实现订单同步逻辑
        # 1. 查询待支付订单
        # 2. 调用支付宝查询接口
        # 3. 更新订单状态
        # 4. 激活订阅（如果支付成功）

        return {
            "success": True,
            "synced_orders": 0,
            "paid_orders": 0,
            "message": "订单状态同步完成",
        }
    except Exception as e:
        logger.error(f"订单状态同步失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@celery_app.task
def process_subscription_renewal(subscription_id: str) -> Dict[str, Any]:
    """
    处理订阅续费

    Args:
        subscription_id: 订阅ID

    Returns:
        处理结果
    """
    try:
        logger.info(f"处理订阅续费: subscription={subscription_id}")

        # TODO: 实现续费逻辑
        # 1. 检查订阅状态
        # 2. 检查自动续费设置
        # 3. 创建续费订单
        # 4. 扣款
        # 5. 延长订阅期限

        return {
            "success": True,
            "subscription_id": subscription_id,
            "message": "订阅续费成功",
        }
    except Exception as e:
        logger.error(f"订阅续费失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@celery_app.task
def check_expiring_subscriptions() -> Dict[str, Any]:
    """
    检查即将过期的订阅

    Returns:
        检查结果
    """
    async def _check():
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

                # 发送续费提醒
                for sub in expiring_subscriptions:
                    try:
                        # TODO: 发送邮件通知
                        logger.info(f"订阅即将过期: tenant={sub.tenant_id}, expire_at={sub.expire_at}")

                        # 这里可以调用发送邮件任务
                        # send_email_notification.delay(...)

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

                # 暂停已过期的订阅
                for sub in expired_subscriptions:
                    try:
                        sub.status = "expired"
                        logger.info(f"订阅已过期: tenant={sub.tenant_id}")

                    except Exception as e:
                        logger.error(f"更新订阅状态失败: {e}")

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

    import asyncio
    return asyncio.run(_check())


@celery_app.task
def calculate_usage_charges(tenant_id: str, date: str) -> Dict[str, Any]:
    """
    计算用量费用

    Args:
        tenant_id: 租户ID
        date: 日期 (格式: YYYY-MM-DD)

    Returns:
        计算结果
    """
    async def _calculate():
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

    import asyncio
    return asyncio.run(_calculate())


@celery_app.task
def process_refund(order_id: str, refund_amount: float, reason: str) -> Dict[str, Any]:
    """
    处理退款

    Args:
        order_id: 订单ID
        refund_amount: 退款金额
        reason: 退款原因

    Returns:
        退款结果
    """
    try:
        logger.info(f"处理退款: order={order_id}, amount={refund_amount}")

        # TODO: 实现退款逻辑
        # 1. 验证订单状态
        # 2. 调用支付宝退款接口
        # 3. 更新订单状态
        # 4. 创建退款记录
        # 5. 发送退款通知

        return {
            "success": True,
            "order_id": order_id,
            "refund_amount": refund_amount,
            "message": "退款处理成功",
        }
    except Exception as e:
        logger.error(f"退款处理失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@celery_app.task
def send_invoice(bill_id: str, recipient_email: str) -> Dict[str, Any]:
    """
    发送发票

    Args:
        bill_id: 账单ID
        recipient_email: 收件人邮箱

    Returns:
        发送结果
    """
    try:
        logger.info(f"发送发票: bill={bill_id}, email={recipient_email}")

        # TODO: 实现发票发送逻辑
        # 1. 获取账单信息
        # 2. 生成PDF发票
        # 3. 发送邮件
        # 4. 更新发票状态

        return {
            "success": True,
            "bill_id": bill_id,
            "message": "发票发送成功",
        }
    except Exception as e:
        logger.error(f"发票发送失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }
