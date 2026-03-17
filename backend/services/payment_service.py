"""
支付服务层

提供支付相关的核心业务逻辑，通过依赖注入使用 PaymentGateway 接口。
"""
import json
import logging
import secrets
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import PaymentException, TenantNotFoundException, ResourceNotFoundException
from models.payment import (
    OrderStatus,
    PaymentChannel,
    PaymentOrder,
    PaymentTransaction,
    PaymentType,
    SubscriptionType,
    TransactionStatus,
    TransactionType,
)
from models.tenant import Subscription, Tenant
from services.payment_gateway import PaymentGateway
from core.config import settings
from core.permissions import ADDON_PACKAGES

logger = logging.getLogger(__name__)


# 套餐配置：plan_type -> (价格元, 天数)
PLAN_CONFIG: Dict[str, tuple[Decimal, int]] = {
    "monthly":     (Decimal("0.10"), 30),
    "quarterly":   (Decimal("0.10"), 90),
    "semi_annual": (Decimal("0.10"), 180),
    "annual":      (Decimal("0.10"), 365),
}

# 加量包配置：addon_key -> (价格, credit_type, credits)
ADDON_CONFIG: Dict[str, tuple[Decimal, str, int]] = {
    "image_addon": (Decimal("0.10"), "image", 50),
    "video_addon": (Decimal("0.10"), "video", 10),
}


class PaymentService:
    """支付服务类"""

    def __init__(
        self,
        db: AsyncSession,
        gateway: Optional[PaymentGateway] = None,
        channel: PaymentChannel = PaymentChannel.ALIPAY,
    ):
        self.db = db
        self.channel = channel
        if gateway is not None:
            self._gateway = gateway
        else:
            self._gateway = self._init_gateway_by_channel(channel)

    @staticmethod
    def _init_gateway_by_channel(channel: PaymentChannel) -> Optional[PaymentGateway]:
        """根据渠道初始化支付网关"""
        if channel == PaymentChannel.ALIPAY:
            from services.alipay_client import get_alipay_client
            return get_alipay_client()
        elif channel == PaymentChannel.WECHAT:
            from services.wechat_pay_client import get_wechat_pay_client
            return get_wechat_pay_client()
        return None

    @staticmethod
    def _init_default_gateway() -> Optional[PaymentGateway]:
        """从配置初始化默认网关（支付宝官方 SDK）"""
        from services.alipay_client import get_alipay_client
        return get_alipay_client()

    @staticmethod
    def generate_order_number() -> str:
        """生成订单编号"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = secrets.token_hex(4).upper()
        return f"ORDER{timestamp}{random_str}"

    @staticmethod
    def get_plan_amount(plan_type: str) -> Decimal:
        """获取套餐价格"""
        if plan_type not in PLAN_CONFIG:
            raise ValueError(f"Invalid plan type: {plan_type}. Valid: {list(PLAN_CONFIG)}")
        return PLAN_CONFIG[plan_type][0]

    @staticmethod
    def get_plan_days(plan_type: str) -> int:
        """获取套餐天数"""
        if plan_type not in PLAN_CONFIG:
            raise ValueError(f"Invalid plan type: {plan_type}")
        return PLAN_CONFIG[plan_type][1]

    async def create_native_payment_order(
        self,
        tenant_id: int,
        plan_type: str,
        subscription_type: SubscriptionType,
        payment_channel: PaymentChannel = PaymentChannel.ALIPAY,
        description: Optional[str] = None,
    ) -> tuple[PaymentOrder, str]:
        """
        创建扫码支付订单

        Args:
            tenant_id: 租户ID
            plan_type: 套餐类型（monthly/quarterly/semi_annual/annual）
            subscription_type: 订阅类型
            payment_channel: 支付渠道
            description: 订单描述

        Returns:
            (订单对象, 二维码URL)
        """
        if not self._gateway:
            raise PaymentException("支付网关未配置，请检查支付配置")

        try:
            # 验证租户
            tenant_stmt = select(Tenant).where(Tenant.id == tenant_id)
            tenant_result = await self.db.execute(tenant_stmt)
            tenant = tenant_result.scalar_one_or_none()
            if not tenant:
                raise TenantNotFoundException(str(tenant_id))

            # 加量包订单走独立逻辑
            if subscription_type == SubscriptionType.ADDON:
                if plan_type not in ADDON_CONFIG:
                    raise PaymentException(f"无效的加量包类型: {plan_type}")
                amount = ADDON_CONFIG[plan_type][0]
                pkg = ADDON_PACKAGES.get(plan_type, {})
                subject = description or pkg.get("name", f"加量包-{plan_type}")
            else:
                amount = self.get_plan_amount(plan_type)
                subject = description or f"电商智能客服-{plan_type}套餐"

            order_number = self.generate_order_number()

            order = PaymentOrder(
                order_number=order_number,
                tenant_id=tenant_id,
                amount=amount,
                currency="CNY",
                payment_channel=payment_channel,
                payment_type=PaymentType.NATIVE,
                status=OrderStatus.PENDING,
                subscription_type=subscription_type,
                plan_type=plan_type,
                duration_months=0,
                expired_at=datetime.now() + timedelta(hours=2),
                description=subject,
            )

            self.db.add(order)
            await self.db.commit()
            await self.db.refresh(order)

            # 调用支付网关
            if payment_channel == PaymentChannel.ALIPAY:
                notify_url = getattr(settings, "alipay_notify_url", "")
            elif payment_channel == PaymentChannel.WECHAT:
                notify_url = getattr(settings, "wechat_notify_url", "")
            else:
                notify_url = ""

            result = await self._gateway.create_native_pay(
                out_trade_no=order_number,
                total_amount=str(amount),
                subject=subject,
                notify_url=notify_url,
            )

            qr_code = result.get("qr_code", "")
            order.qr_code_url = qr_code
            order.payment_url = qr_code
            await self.db.commit()

            logger.info(f"Created {payment_channel.value} payment order: {order_number}, tenant={tenant_id}")
            return order, qr_code

        except (TenantNotFoundException, PaymentException):
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating payment order: {e}")
            raise PaymentException(f"创建支付订单失败: {str(e)}")

    async def create_page_payment_order(
        self,
        tenant_id: int,
        plan_type: str,
        subscription_type: SubscriptionType,
        payment_channel: PaymentChannel = PaymentChannel.ALIPAY,
        description: Optional[str] = None,
        return_url: Optional[str] = None,
    ) -> tuple[PaymentOrder, str]:
        """
        创建电脑网站支付订单

        Returns:
            (订单对象, 跳转URL)
        """
        if not self._gateway:
            raise PaymentException("支付网关未配置，请检查支付配置")

        try:
            tenant_stmt = select(Tenant).where(Tenant.id == tenant_id)
            tenant_result = await self.db.execute(tenant_stmt)
            tenant = tenant_result.scalar_one_or_none()
            if not tenant:
                raise TenantNotFoundException(str(tenant_id))

            if subscription_type == SubscriptionType.ADDON:
                if plan_type not in ADDON_CONFIG:
                    raise PaymentException(f"无效的加量包类型: {plan_type}")
                amount = ADDON_CONFIG[plan_type][0]
                pkg = ADDON_PACKAGES.get(plan_type, {})
                subject = description or pkg.get("name", f"加量包-{plan_type}")
            else:
                amount = self.get_plan_amount(plan_type)
                subject = description or f"电商智能客服-{plan_type}套餐"

            order_number = self.generate_order_number()

            order = PaymentOrder(
                order_number=order_number,
                tenant_id=tenant_id,
                amount=amount,
                currency="CNY",
                payment_channel=payment_channel,
                payment_type=PaymentType.PC,
                status=OrderStatus.PENDING,
                subscription_type=subscription_type,
                plan_type=plan_type,
                duration_months=0,
                expired_at=datetime.now() + timedelta(hours=2),
                description=subject,
            )

            self.db.add(order)
            await self.db.commit()
            await self.db.refresh(order)

            notify_url = getattr(settings, "alipay_notify_url", "")
            effective_return_url = return_url or getattr(settings, "alipay_return_url", "")

            result = await self._gateway.create_page_pay(
                out_trade_no=order_number,
                total_amount=str(amount),
                subject=subject,
                notify_url=notify_url,
                return_url=effective_return_url,
            )

            pay_url = result.get("pay_url", "")
            order.payment_url = pay_url
            await self.db.commit()

            logger.info(f"Created PC payment order: {order_number}, tenant={tenant_id}")
            return order, pay_url

        except (TenantNotFoundException, PaymentException):
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating page payment order: {e}")
            raise PaymentException(f"创建支付订单失败: {str(e)}")

    async def handle_alipay_notify(self, notify_data: Dict[str, str]) -> bool:
        """
        处理支付宝异步回调

        Args:
            notify_data: 回调参数字典

        Returns:
            是否处理成功
        """
        try:
            if not self._gateway:
                logger.error("Payment gateway not initialized")
                return False

            if not self._gateway.verify_notify(notify_data):
                logger.error("Alipay notify signature verification failed")
                return False

            out_trade_no = notify_data.get("out_trade_no")
            trade_no = notify_data.get("trade_no", "")
            trade_status = notify_data.get("trade_status", "")
            total_amount = notify_data.get("total_amount", "0")

            logger.info(
                f"Processing alipay notify: out_trade_no={out_trade_no}, "
                f"trade_no={trade_no}, status={trade_status}"
            )

            # 只处理支付成功的通知
            if trade_status not in ("TRADE_SUCCESS", "TRADE_FINISHED"):
                logger.info(f"Ignoring non-success trade status: {trade_status}")
                return True

            stmt = select(PaymentOrder).where(PaymentOrder.order_number == out_trade_no)
            result = await self.db.execute(stmt)
            order = result.scalar_one_or_none()

            if not order:
                logger.error(f"Order not found: {out_trade_no}")
                return False

            if order.status == OrderStatus.PAID:
                logger.info(f"Order already paid: {out_trade_no}")
                return True

            # 验证金额
            notify_amount = Decimal(total_amount)
            if abs(order.amount - notify_amount) > Decimal("0.01"):
                logger.error(f"Amount mismatch: order={order.amount}, notify={notify_amount}")
                return False

            order.status = OrderStatus.PAID
            order.trade_no = trade_no
            order.paid_at = datetime.now()
            order.callback_data = json.dumps(notify_data, ensure_ascii=False)
            order.callback_count += 1

            transaction = PaymentTransaction(
                order_id=order.id,
                transaction_no=f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}{secrets.token_hex(4).upper()}",
                transaction_type=TransactionType.PAYMENT,
                transaction_status=TransactionStatus.SUCCESS,
                amount=notify_amount,
                currency="CNY",
                third_party_trade_no=trade_no,
                payment_channel=PaymentChannel.ALIPAY,
                transaction_data=json.dumps(notify_data, ensure_ascii=False),
                transaction_time=datetime.now(),
            )
            self.db.add(transaction)

            await self._activate_subscription(order)
            await self.db.commit()

            logger.info(f"Alipay payment success: {out_trade_no}")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error handling alipay notify: {e}")
            return False

    async def handle_wechat_notify(self, notify_data: dict, headers: dict) -> bool:
        """
        处理微信支付异步回调

        Args:
            notify_data: 回调请求体（JSON）
            headers: 回调请求头

        Returns:
            是否处理成功
        """
        try:
            if not self._gateway:
                logger.error("Payment gateway not initialized")
                return False

            # 验证签名并解密数据
            from services.wechat_pay_client import WechatPayClient
            if not isinstance(self._gateway, WechatPayClient):
                logger.error("Gateway is not WechatPayClient")
                return False

            verified, decrypted_data = self._gateway.verify_notify(notify_data, headers)
            if not verified:
                logger.error("Wechat notify signature verification failed")
                return False

            out_trade_no = decrypted_data.get("out_trade_no")
            transaction_id = decrypted_data.get("transaction_id", "")
            trade_state = decrypted_data.get("trade_state", "")
            amount_info = decrypted_data.get("amount", {})
            total_fen = amount_info.get("total", 0)
            total_yuan = Decimal(total_fen) / 100

            logger.info(
                f"Processing wechat notify: out_trade_no={out_trade_no}, "
                f"transaction_id={transaction_id}, state={trade_state}"
            )

            # 只处理支付成功的通知
            if trade_state != "SUCCESS":
                logger.info(f"Ignoring non-success trade state: {trade_state}")
                return True

            stmt = select(PaymentOrder).where(PaymentOrder.order_number == out_trade_no)
            result = await self.db.execute(stmt)
            order = result.scalar_one_or_none()

            if not order:
                logger.error(f"Order not found: {out_trade_no}")
                return False

            if order.status == OrderStatus.PAID:
                logger.info(f"Order already paid: {out_trade_no}")
                return True

            # 验证金额
            if abs(order.amount - total_yuan) > Decimal("0.01"):
                logger.error(f"Amount mismatch: order={order.amount}, notify={total_yuan}")
                return False

            order.status = OrderStatus.PAID
            order.trade_no = transaction_id
            order.paid_at = datetime.now()
            order.callback_data = json.dumps(decrypted_data, ensure_ascii=False)
            order.callback_count += 1

            transaction = PaymentTransaction(
                order_id=order.id,
                transaction_no=f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}{secrets.token_hex(4).upper()}",
                transaction_type=TransactionType.PAYMENT,
                transaction_status=TransactionStatus.SUCCESS,
                amount=total_yuan,
                currency="CNY",
                third_party_trade_no=transaction_id,
                payment_channel=PaymentChannel.WECHAT,
                transaction_data=json.dumps(decrypted_data, ensure_ascii=False),
                transaction_time=datetime.now(),
            )
            self.db.add(transaction)

            await self._activate_subscription(order)
            await self.db.commit()

            logger.info(f"Wechat payment success: {out_trade_no}")
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error handling wechat notify: {e}")
            return False

    async def _activate_subscription(self, order: PaymentOrder) -> None:
        """激活订阅"""
        try:
            # 加量包订单：直接增加余额，不涉及订阅
            if order.subscription_type == SubscriptionType.ADDON:
                from services.quota_service import QuotaService
                quota_service = QuotaService(self.db)
                pkg = ADDON_PACKAGES.get(order.plan_type)
                if pkg:
                    await quota_service.add_addon_credits(
                        tenant_id=str(order.tenant_id),
                        credit_type=pkg["credit_type"],
                        amount=pkg["credits"],
                    )
                logger.info(f"Added addon credits for tenant: {order.tenant_id}, pack: {order.plan_type}")
                return

            stmt = select(Subscription).where(
                Subscription.tenant_id == order.tenant_id,
                Subscription.status == "active",
            )
            result = await self.db.execute(stmt)
            current_subscription = result.scalar_one_or_none()

            now = datetime.now()
            days = self.get_plan_days(order.plan_type)

            if order.subscription_type == SubscriptionType.NEW:
                subscription = Subscription(
                    tenant_id=order.tenant_id,
                    plan_type=order.plan_type,
                    start_date=now,
                    expire_at=now + timedelta(days=days),
                    status="active",
                )
                self.db.add(subscription)
                logger.info(f"Created new subscription for tenant: {order.tenant_id}")

            elif order.subscription_type == SubscriptionType.RENEWAL:
                if current_subscription:
                    base = current_subscription.expire_at if current_subscription.expire_at > now else now
                    current_subscription.expire_at = base + timedelta(days=days)
                    logger.info(f"Renewed subscription for tenant: {order.tenant_id}")
                else:
                    subscription = Subscription(
                        tenant_id=order.tenant_id,
                        plan_type=order.plan_type,
                        start_date=now,
                        expire_at=now + timedelta(days=days),
                        status="active",
                    )
                    self.db.add(subscription)

            elif order.subscription_type == SubscriptionType.UPGRADE:
                if current_subscription:
                    current_subscription.plan_type = order.plan_type
                    logger.info(f"Upgraded subscription for tenant: {order.tenant_id}")
                else:
                    subscription = Subscription(
                        tenant_id=order.tenant_id,
                        plan_type=order.plan_type,
                        start_date=now,
                        expire_at=now + timedelta(days=days),
                        status="active",
                    )
                    self.db.add(subscription)

            # 更新租户当前套餐
            tenant_stmt = select(Tenant).where(Tenant.id == order.tenant_id)
            tenant_result = await self.db.execute(tenant_stmt)
            tenant = tenant_result.scalar_one_or_none()
            if tenant:
                tenant.current_plan = order.plan_type

        except Exception as e:
            logger.error(f"Error activating subscription: {e}")
            raise

    async def query_order_status(self, order_number: str) -> Optional[Dict]:
        """查询订单状态，如果 PENDING 则主动向网关查询"""
        try:
            stmt = select(PaymentOrder).where(PaymentOrder.order_number == order_number)
            result = await self.db.execute(stmt)
            order = result.scalar_one_or_none()

            if not order:
                return None

            if order.status == OrderStatus.PENDING and self._gateway:
                try:
                    gw_result = await self._gateway.query_order(order_number)
                    if gw_result.get("paid"):
                        order.status = OrderStatus.PAID
                        order.trade_no = gw_result.get("trade_no")
                        order.paid_at = datetime.now()
                        await self._activate_subscription(order)
                        await self.db.commit()
                        logger.info(f"Updated order status from gateway query: {order_number}")
                except Exception as e:
                    logger.warning(f"Gateway query failed for {order_number}: {e}")

            return {
                "order_number": order.order_number,
                "status": order.status.value,
                "amount": float(order.amount),
                "trade_no": order.trade_no,
                "qr_code_url": order.qr_code_url,
                "paid_at": order.paid_at.isoformat() if order.paid_at else None,
                "expired_at": order.expired_at.isoformat(),
                "created_at": order.created_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Error querying order status: {e}")
            return None

    async def refund_order(
        self,
        order_number: str,
        refund_amount: Optional[Decimal] = None,
        refund_reason: str = "用户申请退款",
    ) -> Dict:
        """退款"""
        try:
            stmt = select(PaymentOrder).where(PaymentOrder.order_number == order_number)
            result = await self.db.execute(stmt)
            order = result.scalar_one_or_none()

            if not order:
                raise ResourceNotFoundException("订单", order_number)
            if order.status != OrderStatus.PAID:
                raise PaymentException("订单未支付，无法退款")

            if refund_amount is None:
                refund_amount = order.amount
            if refund_amount > order.amount:
                raise PaymentException("退款金额不能大于订单金额")

            if self._gateway:
                refund_result = await self._gateway.refund(
                    out_trade_no=order_number,
                    refund_amount=str(refund_amount),
                    refund_reason=refund_reason,
                )
                if not refund_result.get("success"):
                    raise PaymentException(f"退款失败: {refund_result.get('message', '未知错误')}")

            order.status = OrderStatus.REFUNDED if refund_amount >= order.amount else OrderStatus.REFUNDING

            transaction = PaymentTransaction(
                order_id=order.id,
                transaction_no=f"REFUND{datetime.now().strftime('%Y%m%d%H%M%S')}{secrets.token_hex(4).upper()}",
                transaction_type=TransactionType.REFUND,
                transaction_status=TransactionStatus.SUCCESS,
                amount=refund_amount,
                currency="CNY",
                payment_channel=order.payment_channel,
                transaction_time=datetime.now(),
                remark=refund_reason,
            )
            self.db.add(transaction)
            await self.db.commit()

            logger.info(f"Refund processed: {order_number}, amount={refund_amount}")
            return {"success": True, "refund_amount": float(refund_amount), "message": "退款成功"}

        except (PaymentException, ResourceNotFoundException):
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error processing refund: {e}")
            raise PaymentException(f"退款失败: {str(e)}")
