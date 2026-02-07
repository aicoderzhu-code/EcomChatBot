"""
支付服务层

提供支付相关的核心业务逻辑
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
from services.alipay_client import get_alipay_client
from services.wechat_pay import WechatPayClient, WechatPayConfig, yuan_to_fen, fen_to_yuan
from core.config import settings

logger = logging.getLogger(__name__)


# 套餐价格配置（元/月）
PLAN_PRICES = {
    "basic": Decimal("198.00"),  # 基础版
    "professional": Decimal("598.00"),  # 专业版
    "enterprise": Decimal("1998.00"),  # 企业版
}

# 折扣配置
DURATION_DISCOUNTS = {
    1: Decimal("1.0"),  # 1个月：无折扣
    3: Decimal("0.95"),  # 3个月：95折
    6: Decimal("0.90"),  # 6个月：90折
    12: Decimal("0.85"),  # 12个月：85折
}


class PaymentService:
    """支付服务类"""

    def __init__(self, db: AsyncSession):
        """初始化支付服务"""
        self.db = db
        self.alipay_client = get_alipay_client()
        self.wechat_client = self._init_wechat_client()

    @staticmethod
    def generate_order_number() -> str:
        """生成订单编号"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = secrets.token_hex(4).upper()
        return f"ORDER{timestamp}{random_str}"

    @staticmethod
    def calculate_amount(plan_type: str, duration_months: int) -> Decimal:
        """
        计算订单金额

        Args:
            plan_type: 套餐类型
            duration_months: 订阅时长（月）

        Returns:
            订单金额（元）
        """
        if plan_type not in PLAN_PRICES:
            raise ValueError(f"Invalid plan type: {plan_type}")
        
        if duration_months not in DURATION_DISCOUNTS:
            raise ValueError(f"Invalid duration months: {duration_months}")
        
        # 基础价格 * 时长 * 折扣
        monthly_price = PLAN_PRICES[plan_type]
        discount = DURATION_DISCOUNTS[duration_months]
        total_amount = monthly_price * duration_months * discount
        
        # 保留2位小数
        return total_amount.quantize(Decimal("0.01"))

    async def create_payment_order(
        self,
        tenant_id: int,
        plan_type: str,
        duration_months: int,
        payment_type: PaymentType,
        subscription_type: SubscriptionType,
        description: Optional[str] = None,
    ) -> tuple[PaymentOrder, str]:
        """
        创建支付订单

        Args:
            tenant_id: 租户ID
            plan_type: 套餐类型
            duration_months: 订阅时长（月）
            payment_type: 支付类型（PC/移动）
            subscription_type: 订阅类型（新订阅/续费/升级）
            description: 订单描述

        Returns:
            (订单对象, 支付HTML)
        """
        try:
            # 验证租户
            tenant_stmt = select(Tenant).where(Tenant.id == tenant_id)
            tenant_result = await self.db.execute(tenant_stmt)
            tenant = tenant_result.scalar_one_or_none()

            if not tenant:
                raise TenantNotFoundException(str(tenant_id))
            
            # 计算订单金额
            amount = self.calculate_amount(plan_type, duration_months)
            
            # 生成订单号
            order_number = self.generate_order_number()
            
            # 创建订单
            order = PaymentOrder(
                order_number=order_number,
                tenant_id=tenant_id,
                amount=amount,
                currency="CNY",
                payment_channel=PaymentChannel.ALIPAY,
                payment_type=payment_type,
                status=OrderStatus.PENDING,
                subscription_type=subscription_type,
                plan_type=plan_type,
                duration_months=duration_months,
                expired_at=datetime.now() + timedelta(hours=24),
                description=description or f"{plan_type}套餐-{duration_months}个月",
            )
            
            self.db.add(order)
            await self.db.commit()
            await self.db.refresh(order)
            
            # 生成支付HTML
            subject = f"电商智能客服-{plan_type}套餐"
            
            if payment_type == PaymentType.PC:
                payment_html = self.alipay_client.create_page_pay(
                    order_number=order_number,
                    total_amount=amount,
                    subject=subject,
                )
            else:  # MOBILE
                payment_html = self.alipay_client.create_wap_pay(
                    order_number=order_number,
                    total_amount=amount,
                    subject=subject,
                )
            
            # 更新订单的支付URL
            order.payment_url = payment_html
            await self.db.commit()
            
            logger.info(
                f"Created payment order: {order_number}, "
                f"tenant_id: {tenant_id}, "
                f"amount: {amount}, "
                f"type: {payment_type}"
            )
            
            return order, payment_html

        except (TenantNotFoundException, PaymentException):
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating payment order: {e}")
            raise PaymentException(f"创建支付订单失败: {str(e)}")

    async def handle_alipay_notify(self, notify_data: Dict[str, str]) -> bool:
        """
        处理支付宝异步回调

        Args:
            notify_data: 支付宝回调参数

        Returns:
            是否处理成功
        """
        try:
            # 验证签名
            if not self.alipay_client.verify_notify(notify_data):
                logger.error("Alipay notify signature verification failed")
                return False
            
            # 提取关键信息
            out_trade_no = notify_data.get("out_trade_no")
            trade_no = notify_data.get("trade_no")
            trade_status = notify_data.get("trade_status")
            total_amount = Decimal(notify_data.get("total_amount", "0"))
            
            logger.info(
                f"Processing alipay notify: out_trade_no={out_trade_no}, "
                f"trade_no={trade_no}, trade_status={trade_status}"
            )
            
            # 查询订单
            stmt = select(PaymentOrder).where(PaymentOrder.order_number == out_trade_no)
            result = await self.db.execute(stmt)
            order = result.scalar_one_or_none()
            
            if not order:
                logger.error(f"Order not found: {out_trade_no}")
                return False
            
            # 幂等性检查：如果订单已经是已支付状态，直接返回成功
            if order.status == OrderStatus.PAID:
                logger.info(f"Order already paid: {out_trade_no}, returning success")
                return True
            
            # 验证金额
            if abs(order.amount - total_amount) > Decimal("0.01"):
                logger.error(
                    f"Amount mismatch: order_amount={order.amount}, "
                    f"notify_amount={total_amount}"
                )
                return False
            
            # 处理支付成功
            if trade_status == "TRADE_SUCCESS":
                # 更新订单状态
                order.status = OrderStatus.PAID
                order.trade_no = trade_no
                order.paid_at = datetime.now()
                order.callback_data = json.dumps(notify_data, ensure_ascii=False)
                order.callback_count += 1
                
                # 创建支付交易记录
                transaction = PaymentTransaction(
                    order_id=order.id,
                    transaction_no=f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}{secrets.token_hex(4).upper()}",
                    transaction_type=TransactionType.PAYMENT,
                    transaction_status=TransactionStatus.SUCCESS,
                    amount=total_amount,
                    currency="CNY",
                    third_party_trade_no=trade_no,
                    payment_channel=PaymentChannel.ALIPAY,
                    transaction_data=json.dumps(notify_data, ensure_ascii=False),
                    transaction_time=datetime.now(),
                )
                
                self.db.add(transaction)
                
                # 激活订阅
                await self._activate_subscription(order)
                
                await self.db.commit()
                
                logger.info(f"Payment success processed: {out_trade_no}")
                return True
            
            else:
                logger.warning(f"Trade status not success: {trade_status}")
                return False
                
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error handling alipay notify: {e}")
            return False

    async def _activate_subscription(self, order: PaymentOrder) -> None:
        """
        激活订阅

        Args:
            order: 支付订单
        """
        try:
            # 查询租户当前订阅
            stmt = select(Subscription).where(
                Subscription.tenant_id == order.tenant_id,
                Subscription.status == "active"
            )
            result = await self.db.execute(stmt)
            current_subscription = result.scalar_one_or_none()
            
            now = datetime.now()
            
            if order.subscription_type == SubscriptionType.NEW:
                # 新订阅：创建订阅记录
                subscription = Subscription(
                    tenant_id=order.tenant_id,
                    plan_type=order.plan_type,
                    start_date=now,
                    end_date=now + timedelta(days=30 * order.duration_months),
                    status="active",
                )
                self.db.add(subscription)
                logger.info(f"Created new subscription for tenant: {order.tenant_id}")
                
            elif order.subscription_type == SubscriptionType.RENEWAL:
                # 续费：延长订阅时间
                if current_subscription:
                    # 如果当前订阅还未过期，从结束时间开始延长
                    if current_subscription.end_date > now:
                        current_subscription.end_date += timedelta(days=30 * order.duration_months)
                    else:
                        # 如果已过期，从现在开始
                        current_subscription.start_date = now
                        current_subscription.end_date = now + timedelta(days=30 * order.duration_months)
                    
                    logger.info(f"Renewed subscription for tenant: {order.tenant_id}")
                else:
                    # 如果没有当前订阅，创建新订阅
                    subscription = Subscription(
                        tenant_id=order.tenant_id,
                        plan_type=order.plan_type,
                        start_date=now,
                        end_date=now + timedelta(days=30 * order.duration_months),
                        status="active",
                    )
                    self.db.add(subscription)
                    logger.info(f"Created subscription (renewal) for tenant: {order.tenant_id}")
            
            elif order.subscription_type == SubscriptionType.UPGRADE:
                # 升级：更新套餐类型
                if current_subscription:
                    current_subscription.plan_type = order.plan_type
                    # 保持时间不变
                    logger.info(f"Upgraded subscription for tenant: {order.tenant_id}")
                else:
                    # 如果没有当前订阅，创建新订阅
                    subscription = Subscription(
                        tenant_id=order.tenant_id,
                        plan_type=order.plan_type,
                        start_date=now,
                        end_date=now + timedelta(days=30 * order.duration_months),
                        status="active",
                    )
                    self.db.add(subscription)
                    logger.info(f"Created subscription (upgrade) for tenant: {order.tenant_id}")
            
            # 更新租户的当前套餐
            tenant_stmt = select(Tenant).where(Tenant.id == order.tenant_id)
            tenant_result = await self.db.execute(tenant_stmt)
            tenant = tenant_result.scalar_one_or_none()
            if tenant:
                tenant.current_plan = order.plan_type
            
        except Exception as e:
            logger.error(f"Error activating subscription: {e}")
            raise

    async def query_order_status(self, order_number: str) -> Optional[Dict]:
        """
        查询订单状态

        Args:
            order_number: 订单编号

        Returns:
            订单信息字典
        """
        try:
            # 查询本地订单
            stmt = select(PaymentOrder).where(PaymentOrder.order_number == order_number)
            result = await self.db.execute(stmt)
            order = result.scalar_one_or_none()
            
            if not order:
                return None
            
            # 如果订单未支付，尝试从支付宝查询最新状态
            if order.status == OrderStatus.PENDING:
                alipay_result = self.alipay_client.query_order(order_number=order_number)
                if alipay_result and alipay_result.get("trade_status") == "TRADE_SUCCESS":
                    # 更新本地订单状态
                    order.status = OrderStatus.PAID
                    order.trade_no = alipay_result.get("trade_no")
                    order.paid_at = datetime.now()
                    await self.db.commit()
                    
                    logger.info(f"Updated order status from alipay query: {order_number}")
            
            return {
                "order_number": order.order_number,
                "status": order.status.value,
                "amount": float(order.amount),
                "trade_no": order.trade_no,
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
        """
        退款

        Args:
            order_number: 订单编号
            refund_amount: 退款金额（不填则全额退款）
            refund_reason: 退款原因

        Returns:
            退款结果字典
        """
        try:
            # 查询订单
            stmt = select(PaymentOrder).where(PaymentOrder.order_number == order_number)
            result = await self.db.execute(stmt)
            order = result.scalar_one_or_none()

            if not order:
                raise ResourceNotFoundException("订单", order_number)

            if order.status != OrderStatus.PAID:
                raise PaymentException("订单未支付，无法退款")

            # 默认全额退款
            if refund_amount is None:
                refund_amount = order.amount

            if refund_amount > order.amount:
                raise PaymentException("退款金额不能大于订单金额")
            
            # 调用支付宝退款接口
            refund_result = self.alipay_client.refund(
                order_number=order_number,
                refund_amount=refund_amount,
                refund_reason=refund_reason,
                trade_no=order.trade_no,
            )

            if not refund_result:
                raise PaymentException("退款失败")

            # 更新订单状态
            if refund_amount >= order.amount:
                order.status = OrderStatus.REFUNDED
            else:
                order.status = OrderStatus.REFUNDING
            
            # 创建退款交易记录
            transaction = PaymentTransaction(
                order_id=order.id,
                transaction_no=f"REFUND{datetime.now().strftime('%Y%m%d%H%M%S')}{secrets.token_hex(4).upper()}",
                transaction_type=TransactionType.REFUND,
                transaction_status=TransactionStatus.SUCCESS,
                amount=refund_amount,
                currency="CNY",
                payment_channel=PaymentChannel.ALIPAY,
                transaction_data=json.dumps(refund_result, ensure_ascii=False),
                transaction_time=datetime.now(),
                remark=refund_reason,
            )
            
            self.db.add(transaction)
            await self.db.commit()
            
            logger.info(
                f"Refund processed: {order_number}, "
                f"amount: {refund_amount}, "
                f"reason: {refund_reason}"
            )
            
            return {
                "success": True,
                "refund_amount": float(refund_amount),
                "message": "退款成功",
            }

        except (PaymentException, ResourceNotFoundException):
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error processing refund: {e}")
            raise PaymentException(f"退款失败: {str(e)}")

    # ===== 微信支付相关方法 =====

    def _init_wechat_client(self) -> Optional[WechatPayClient]:
        """初始化微信支付客户端"""
        try:
            # 从配置中获取微信支付参数
            wechat_config = WechatPayConfig(
                app_id=getattr(settings, 'wechat_app_id', ''),
                mch_id=getattr(settings, 'wechat_mch_id', ''),
                api_v3_key=getattr(settings, 'wechat_api_v3_key', ''),
                private_key_path=getattr(settings, 'wechat_private_key_path', ''),
                serial_no=getattr(settings, 'wechat_serial_no', ''),
                notify_url=getattr(settings, 'wechat_notify_url', '')
            )

            # 验证配置是否完整
            if not all([wechat_config.app_id, wechat_config.mch_id, wechat_config.api_v3_key]):
                logger.warning("微信支付配置不完整,微信支付功能将不可用")
                return None

            return WechatPayClient(wechat_config)
        except Exception as e:
            logger.error(f"初始化微信支付客户端失败: {e}")
            return None

    async def create_wechat_payment_order(
        self,
        tenant_id: int,
        plan_type: str,
        duration_months: int,
        payment_method: str,  # "native" 或 "jsapi"
        subscription_type: SubscriptionType,
        openid: Optional[str] = None,  # JSAPI支付需要
        description: Optional[str] = None,
    ) -> tuple[PaymentOrder, Dict[str, Any]]:
        """
        创建微信支付订单

        Args:
            tenant_id: 租户ID
            plan_type: 套餐类型
            duration_months: 订阅时长(月)
            payment_method: 支付方式(native/jsapi)
            subscription_type: 订阅类型
            openid: 用户openid(JSAPI支付必需)
            description: 订单描述

        Returns:
            (订单对象, 支付参数)
            - native: {"code_url": "weixin://..."}
            - jsapi: {"appId": "...", "timeStamp": "...", ...}
        """
        if not self.wechat_client:
            raise PaymentException("微信支付未配置")

        try:
            # 验证租户
            tenant_stmt = select(Tenant).where(Tenant.id == tenant_id)
            tenant_result = await self.db.execute(tenant_stmt)
            tenant = tenant_result.scalar_one_or_none()

            if not tenant:
                raise TenantNotFoundException(str(tenant_id))

            # 计算订单金额
            amount_yuan = self.calculate_amount(plan_type, duration_months)
            amount_fen = yuan_to_fen(float(amount_yuan))

            # 生成订单号
            order_number = self.generate_order_number()

            # 创建订单
            order = PaymentOrder(
                order_number=order_number,
                tenant_id=tenant_id,
                amount=amount_yuan,
                currency="CNY",
                payment_channel=PaymentChannel.WECHAT,
                payment_type=PaymentType.PC if payment_method == "native" else PaymentType.MOBILE,
                status=OrderStatus.PENDING,
                subscription_type=subscription_type,
                plan_type=plan_type,
                duration_months=duration_months,
                expired_at=datetime.now() + timedelta(hours=2),  # 微信支付订单2小时过期
                description=description or f"{plan_type}套餐-{duration_months}个月",
            )

            self.db.add(order)
            await self.db.commit()
            await self.db.refresh(order)

            # 调用微信支付API
            desc = f"电商智能客服-{plan_type}套餐"
            attach_data = json.dumps({
                "tenant_id": tenant_id,
                "subscription_type": subscription_type.value
            })

            if payment_method == "native":
                # Native支付(扫码)
                result = await self.wechat_client.create_native_order(
                    order_number=order_number,
                    amount=amount_fen,
                    description=desc,
                    attach=attach_data
                )
            elif payment_method == "jsapi":
                # JSAPI支付(公众号/小程序)
                if not openid:
                    raise PaymentException("JSAPI支付需要提供openid")

                result = await self.wechat_client.create_jsapi_order(
                    order_number=order_number,
                    amount=amount_fen,
                    description=desc,
                    openid=openid,
                    attach=attach_data
                )
            else:
                raise PaymentException(f"不支持的支付方式: {payment_method}")

            # 更新订单的支付URL
            order.payment_url = json.dumps(result, ensure_ascii=False)
            await self.db.commit()

            logger.info(
                f"Created wechat payment order: {order_number}, "
                f"tenant_id: {tenant_id}, "
                f"amount: {amount_yuan}, "
                f"method: {payment_method}"
            )

            return order, result

        except (TenantNotFoundException, PaymentException):
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating wechat payment order: {e}")
            raise PaymentException(f"创建微信支付订单失败: {str(e)}")

    async def handle_wechat_notify(self, headers: Dict[str, str], body: str) -> bool:
        """
        处理微信支付异步回调

        Args:
            headers: 请求头
            body: 请求体

        Returns:
            是否处理成功
        """
        if not self.wechat_client:
            logger.error("Wechat client not initialized")
            return False

        try:
            # 验证签名并解密(异步方法)
            notify_data = await self.wechat_client.verify_notification(headers, body)

            # 提取关键信息
            out_trade_no = notify_data.get("out_trade_no")
            transaction_id = notify_data.get("transaction_id")
            trade_state = notify_data.get("trade_state")
            amount_dict = notify_data.get("amount", {})
            total_amount_fen = amount_dict.get("total", 0)
            total_amount = Decimal(str(fen_to_yuan(total_amount_fen)))

            logger.info(
                f"Processing wechat notify: out_trade_no={out_trade_no}, "
                f"transaction_id={transaction_id}, trade_state={trade_state}"
            )

            # 查询订单
            stmt = select(PaymentOrder).where(PaymentOrder.order_number == out_trade_no)
            result = await self.db.execute(stmt)
            order = result.scalar_one_or_none()

            if not order:
                logger.error(f"Order not found: {out_trade_no}")
                return False

            # 幂等性检查
            if order.status == OrderStatus.PAID:
                logger.info(f"Order already paid: {out_trade_no}, returning success")
                return True

            # 验证金额
            if abs(order.amount - total_amount) > Decimal("0.01"):
                logger.error(
                    f"Amount mismatch: order_amount={order.amount}, "
                    f"notify_amount={total_amount}"
                )
                return False

            # 处理支付成功
            if trade_state == "SUCCESS":
                # 更新订单状态
                order.status = OrderStatus.PAID
                order.trade_no = transaction_id
                order.paid_at = datetime.now()
                order.callback_data = json.dumps(notify_data, ensure_ascii=False)
                order.callback_count += 1

                # 创建支付交易记录
                transaction = PaymentTransaction(
                    order_id=order.id,
                    transaction_no=f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}{secrets.token_hex(4).upper()}",
                    transaction_type=TransactionType.PAYMENT,
                    transaction_status=TransactionStatus.SUCCESS,
                    amount=total_amount,
                    currency="CNY",
                    third_party_trade_no=transaction_id,
                    payment_channel=PaymentChannel.WECHAT,
                    transaction_data=json.dumps(notify_data, ensure_ascii=False),
                    transaction_time=datetime.now(),
                )

                self.db.add(transaction)

                # 激活订阅
                await self._activate_subscription(order)

                await self.db.commit()

                logger.info(f"Wechat payment success processed: {out_trade_no}")
                return True
            else:
                logger.warning(f"Trade state not success: {trade_state}")
                return False

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error handling wechat notify: {e}")
            return False

    async def refund_wechat_order(
        self,
        order_number: str,
        refund_amount: Optional[Decimal] = None,
        refund_reason: str = "用户申请退款",
    ) -> Dict:
        """
        微信支付退款

        Args:
            order_number: 订单编号
            refund_amount: 退款金额(不填则全额退款)
            refund_reason: 退款原因

        Returns:
            退款结果字典
        """
        if not self.wechat_client:
            raise PaymentException("微信支付未配置")

        try:
            # 查询订单
            stmt = select(PaymentOrder).where(PaymentOrder.order_number == order_number)
            result = await self.db.execute(stmt)
            order = result.scalar_one_or_none()

            if not order:
                raise ResourceNotFoundException("订单", order_number)

            if order.status != OrderStatus.PAID:
                raise PaymentException("订单未支付,无法退款")

            if order.payment_channel != PaymentChannel.WECHAT:
                raise PaymentException("该订单不是微信支付订单")

            # 默认全额退款
            if refund_amount is None:
                refund_amount = order.amount

            if refund_amount > order.amount:
                raise PaymentException("退款金额不能大于订单金额")

            # 生成退款单号
            refund_number = f"REFUND{datetime.now().strftime('%Y%m%d%H%M%S')}{secrets.token_hex(4).upper()}"

            # 调用微信退款接口
            refund_result = await self.wechat_client.refund(
                order_number=order_number,
                refund_number=refund_number,
                amount=yuan_to_fen(float(refund_amount)),
                total_amount=yuan_to_fen(float(order.amount)),
                reason=refund_reason
            )

            # 更新订单状态
            if refund_amount >= order.amount:
                order.status = OrderStatus.REFUNDED
            else:
                order.status = OrderStatus.REFUNDING

            # 创建退款交易记录
            transaction = PaymentTransaction(
                order_id=order.id,
                transaction_no=refund_number,
                transaction_type=TransactionType.REFUND,
                transaction_status=TransactionStatus.SUCCESS,
                amount=refund_amount,
                currency="CNY",
                payment_channel=PaymentChannel.WECHAT,
                transaction_data=json.dumps(refund_result, ensure_ascii=False),
                transaction_time=datetime.now(),
                remark=refund_reason,
            )

            self.db.add(transaction)
            await self.db.commit()

            logger.info(
                f"Wechat refund processed: {order_number}, "
                f"amount: {refund_amount}, "
                f"reason: {refund_reason}"
            )

            return {
                "success": True,
                "refund_amount": float(refund_amount),
                "refund_id": refund_result.get("refund_id"),
                "message": "退款成功",
            }

        except (PaymentException, ResourceNotFoundException):
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error processing wechat refund: {e}")
            raise PaymentException(f"微信退款失败: {str(e)}")
