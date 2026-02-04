"""
支付宝客户端封装

提供支付宝 API 的统一调用接口
"""
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional

from alipay import AliPay
from alipay.exceptions import AliPayException

from core.config import settings

logger = logging.getLogger(__name__)


class AlipayClient:
    """支付宝客户端封装类"""

    def __init__(self):
        """初始化支付宝客户端"""
        try:
            # 读取密钥文件
            with open(settings.ALIPAY_PRIVATE_KEY_PATH, 'r') as f:
                app_private_key_string = f.read()
            
            with open(settings.ALIPAY_PUBLIC_KEY_PATH, 'r') as f:
                alipay_public_key_string = f.read()
            
            # 初始化 AliPay 对象
            self.client = AliPay(
                appid=settings.ALIPAY_APPID,
                app_notify_url=settings.ALIPAY_NOTIFY_URL,
                app_private_key_string=app_private_key_string,
                alipay_public_key_string=alipay_public_key_string,
                sign_type="RSA2",
                debug=settings.ALIPAY_SANDBOX,  # 沙箱模式
            )
            
            # 网关地址
            self.gateway = (
                settings.ALIPAY_SANDBOX_GATEWAY 
                if settings.ALIPAY_SANDBOX 
                else settings.ALIPAY_GATEWAY_URL
            )
            
            logger.info(
                f"Alipay client initialized. Sandbox: {settings.ALIPAY_SANDBOX}, "
                f"Gateway: {self.gateway}"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize Alipay client: {e}")
            raise

    def create_page_pay(
        self,
        order_number: str,
        total_amount: Decimal,
        subject: str,
        return_url: Optional[str] = None,
        timeout_express: str = "24h",
    ) -> str:
        """
        创建 PC 网站支付

        Args:
            order_number: 商户订单号
            total_amount: 订单金额（元）
            subject: 订单标题
            return_url: 同步返回地址
            timeout_express: 订单超时时间

        Returns:
            支付表单 HTML（自动提交）
        """
        try:
            # 构建订单数据
            order_data = {
                "out_trade_no": order_number,
                "total_amount": str(total_amount),
                "subject": subject,
                "product_code": "FAST_INSTANT_TRADE_PAY",
                "timeout_express": timeout_express,
            }
            
            # 生成支付 URL
            order_string = self.client.api_alipay_trade_page_pay(
                **order_data,
                return_url=return_url or settings.ALIPAY_RETURN_URL,
            )
            
            # 构建完整的支付 URL
            payment_url = f"{self.gateway}?{order_string}"
            
            # 构建自动提交的 HTML 表单
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>正在跳转到支付宝...</title>
            </head>
            <body>
                <p style="text-align:center;margin-top:50px;">正在跳转到支付宝支付页面，请稍候...</p>
                <script>
                    window.location.href = "{payment_url}";
                </script>
            </body>
            </html>
            """
            
            logger.info(f"Created page pay for order: {order_number}, amount: {total_amount}")
            return html
            
        except AliPayException as e:
            logger.error(f"Alipay API error in create_page_pay: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in create_page_pay: {e}")
            raise

    def create_wap_pay(
        self,
        order_number: str,
        total_amount: Decimal,
        subject: str,
        return_url: Optional[str] = None,
        timeout_express: str = "24h",
    ) -> str:
        """
        创建手机网站支付

        Args:
            order_number: 商户订单号
            total_amount: 订单金额（元）
            subject: 订单标题
            return_url: 同步返回地址
            timeout_express: 订单超时时间

        Returns:
            支付表单 HTML（自动提交）
        """
        try:
            # 构建订单数据
            order_data = {
                "out_trade_no": order_number,
                "total_amount": str(total_amount),
                "subject": subject,
                "product_code": "QUICK_WAP_WAY",
                "timeout_express": timeout_express,
            }
            
            # 生成支付 URL
            order_string = self.client.api_alipay_trade_wap_pay(
                **order_data,
                return_url=return_url or settings.ALIPAY_RETURN_URL,
            )
            
            # 构建完整的支付 URL
            payment_url = f"{self.gateway}?{order_string}"
            
            # 构建自动提交的 HTML 表单（移动端适配）
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>正在跳转到支付宝...</title>
            </head>
            <body>
                <p style="text-align:center;margin-top:50px;">正在跳转到支付宝支付页面，请稍候...</p>
                <script>
                    window.location.href = "{payment_url}";
                </script>
            </body>
            </html>
            """
            
            logger.info(f"Created wap pay for order: {order_number}, amount: {total_amount}")
            return html
            
        except AliPayException as e:
            logger.error(f"Alipay API error in create_wap_pay: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in create_wap_pay: {e}")
            raise

    def verify_notify(self, data: Dict[str, str]) -> bool:
        """
        验证支付宝异步通知签名

        Args:
            data: 支付宝回调参数

        Returns:
            签名是否有效
        """
        try:
            signature = data.pop("sign", None)
            if not signature:
                logger.warning("No signature in notify data")
                return False
            
            # 验证签名
            result = self.client.verify(data, signature)
            
            if result:
                logger.info(f"Notify signature verified for trade_no: {data.get('trade_no')}")
            else:
                logger.warning(f"Notify signature verification failed for trade_no: {data.get('trade_no')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error verifying notify signature: {e}")
            return False

    def query_order(self, order_number: Optional[str] = None, trade_no: Optional[str] = None) -> Optional[Dict]:
        """
        查询订单支付状态

        Args:
            order_number: 商户订单号
            trade_no: 支付宝交易号

        Returns:
            订单信息字典，查询失败返回 None
        """
        if not order_number and not trade_no:
            raise ValueError("order_number or trade_no must be provided")
        
        try:
            # 构建查询参数
            params = {}
            if order_number:
                params["out_trade_no"] = order_number
            if trade_no:
                params["trade_no"] = trade_no
            
            # 调用查询接口
            result = self.client.api_alipay_trade_query(**params)
            
            if result.get("code") == "10000":
                logger.info(f"Order query success: {order_number or trade_no}")
                return result
            else:
                logger.warning(
                    f"Order query failed: {order_number or trade_no}, "
                    f"code: {result.get('code')}, msg: {result.get('msg')}"
                )
                return None
                
        except AliPayException as e:
            logger.error(f"Alipay API error in query_order: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in query_order: {e}")
            return None

    def refund(
        self,
        order_number: str,
        refund_amount: Decimal,
        refund_reason: str,
        trade_no: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        申请退款

        Args:
            order_number: 商户订单号
            refund_amount: 退款金额（元）
            refund_reason: 退款原因
            trade_no: 支付宝交易号（可选）

        Returns:
            退款结果字典，失败返回 None
        """
        try:
            # 构建退款请求参数
            params = {
                "out_trade_no": order_number,
                "refund_amount": str(refund_amount),
                "refund_reason": refund_reason,
            }
            
            if trade_no:
                params["trade_no"] = trade_no
            
            # 调用退款接口
            result = self.client.api_alipay_trade_refund(**params)
            
            if result.get("code") == "10000":
                logger.info(
                    f"Refund success: {order_number}, "
                    f"amount: {refund_amount}, "
                    f"fund_change: {result.get('fund_change')}"
                )
                return result
            else:
                logger.error(
                    f"Refund failed: {order_number}, "
                    f"code: {result.get('code')}, "
                    f"msg: {result.get('msg')}, "
                    f"sub_code: {result.get('sub_code')}, "
                    f"sub_msg: {result.get('sub_msg')}"
                )
                return None
                
        except AliPayException as e:
            logger.error(f"Alipay API error in refund: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in refund: {e}")
            return None


# 全局单例
_alipay_client: Optional[AlipayClient] = None


def get_alipay_client() -> AlipayClient:
    """获取支付宝客户端单例"""
    global _alipay_client
    if _alipay_client is None:
        _alipay_client = AlipayClient()
    return _alipay_client
