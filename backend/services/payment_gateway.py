"""
支付网关抽象接口

定义统一的支付网关 ABC，所有支付渠道实现此接口。
"""
from abc import ABC, abstractmethod


class PaymentGateway(ABC):
    """支付网关抽象基类"""

    @abstractmethod
    async def create_native_pay(
        self,
        out_trade_no: str,
        total_fee: str,
        body: str,
        notify_url: str,
        channel: str,
        attach: str = "",
    ) -> dict:
        """
        创建扫码支付订单

        Args:
            out_trade_no: 商户订单号
            total_fee: 订单金额（元，字符串）
            body: 商品描述
            notify_url: 回调通知地址
            channel: 支付渠道 "wechat" | "alipay"
            attach: 附加数据（可选）

        Returns:
            {"qr_url": str, "qr_base64": str | None}
        """
        ...

    @abstractmethod
    async def query_order(self, out_trade_no: str, channel: str) -> dict:
        """
        查询订单状态

        Args:
            out_trade_no: 商户订单号
            channel: 支付渠道 "wechat" | "alipay"

        Returns:
            {"paid": bool, "trade_no": str, "amount": str}
        """
        ...

    @abstractmethod
    def verify_notify(self, params: dict) -> bool:
        """
        验证回调签名

        Args:
            params: 回调参数字典

        Returns:
            签名是否合法
        """
        ...

    @abstractmethod
    async def refund(
        self,
        out_trade_no: str,
        refund_amount: str,
        refund_reason: str,
        channel: str,
    ) -> dict:
        """
        申请退款

        Args:
            out_trade_no: 商户订单号
            refund_amount: 退款金额（元，字符串）
            refund_reason: 退款原因
            channel: 支付渠道 "wechat" | "alipay"

        Returns:
            {"success": bool, "refund_no": str}
        """
        ...
