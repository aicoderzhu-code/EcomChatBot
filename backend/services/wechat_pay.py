"""
微信支付服务(API v3)

支持功能:
- Native支付(扫码支付)
- JSAPI支付(公众号/小程序支付)
- 订单查询和关闭
- 退款
- 回调通知验证和解密
- 平台证书管理和签名验证
"""
import base64
import hashlib
import json
import logging
import time
import uuid
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography import x509

logger = logging.getLogger(__name__)


@dataclass
class WechatPayConfig:
    """微信支付配置"""
    app_id: str              # 应用ID(公众号APPID或小程序APPID)
    mch_id: str              # 商户号
    api_v3_key: str          # APIv3密钥(用于回调解密)
    private_key_path: str    # 商户私钥路径
    serial_no: str           # 商户证书序列号
    notify_url: str          # 支付结果通知URL
    cert_path: Optional[str] = None  # 商户证书路径(可选)


class WechatCertificateManager:
    """
    微信平台证书管理器

    负责:
    - 从微信API下载平台证书
    - 解密证书内容
    - 缓存证书(内存+可选Redis)
    - 自动刷新过期证书
    """

    # 证书缓存TTL(7天)
    CACHE_TTL_SECONDS = 7 * 24 * 60 * 60

    def __init__(
        self,
        mch_id: str,
        api_v3_key: str,
        private_key,
        serial_no: str,
        redis_client=None
    ):
        """
        初始化证书管理器

        Args:
            mch_id: 商户号
            api_v3_key: APIv3密钥
            private_key: 商户私钥对象
            serial_no: 商户证书序列号
            redis_client: Redis客户端(可选,用于分布式缓存)
        """
        self.mch_id = mch_id
        self.api_v3_key = api_v3_key
        self.private_key = private_key
        self.serial_no = serial_no
        self.redis_client = redis_client

        # 内存缓存: {serial_no: (certificate, expire_time)}
        self._cert_cache: Dict[str, tuple] = {}

    async def get_certificate(self, serial_no: str) -> Optional[x509.Certificate]:
        """
        获取指定序列号的平台证书

        Args:
            serial_no: 证书序列号

        Returns:
            证书对象,未找到返回None
        """
        # 1. 检查内存缓存
        if serial_no in self._cert_cache:
            cert, expire_time = self._cert_cache[serial_no]
            if datetime.utcnow() < expire_time:
                return cert

        # 2. 检查Redis缓存(如果可用)
        if self.redis_client:
            try:
                cache_key = f"wechat_cert:{serial_no}"
                cert_pem = await self.redis_client.get(cache_key)
                if cert_pem:
                    cert = x509.load_pem_x509_certificate(
                        cert_pem.encode() if isinstance(cert_pem, str) else cert_pem,
                        default_backend()
                    )
                    # 更新内存缓存
                    self._cert_cache[serial_no] = (
                        cert,
                        datetime.utcnow() + timedelta(seconds=self.CACHE_TTL_SECONDS)
                    )
                    return cert
            except Exception as e:
                logger.warning(f"Failed to get certificate from Redis: {e}")

        # 3. 从微信API下载证书
        await self._download_certificates()

        # 4. 再次检查缓存
        if serial_no in self._cert_cache:
            cert, _ = self._cert_cache[serial_no]
            return cert

        logger.error(f"Certificate not found for serial_no: {serial_no}")
        return None

    async def _download_certificates(self) -> None:
        """从微信API下载平台证书"""
        import aiohttp

        url = "https://api.mch.weixin.qq.com/v3/certificates"

        timestamp = int(time.time())
        nonce = str(uuid.uuid4()).replace("-", "")

        # 生成签名
        sign_str = f"GET\n/v3/certificates\n{timestamp}\n{nonce}\n\n"
        signature_bytes = self.private_key.sign(
            sign_str.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        signature = base64.b64encode(signature_bytes).decode('utf-8')

        # 构造Authorization头
        auth_header = (
            f'WECHATPAY2-SHA256-RSA2048 '
            f'mchid="{self.mch_id}",'
            f'nonce_str="{nonce}",'
            f'timestamp="{timestamp}",'
            f'serial_no="{self.serial_no}",'
            f'signature="{signature}"'
        )

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": auth_header,
            "User-Agent": "EcomChatBot/1.0"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"Failed to download certificates: {resp.status} - {error_text}")
                        return

                    data = await resp.json()
                    certificates = data.get("data", [])

                    for cert_data in certificates:
                        serial_no = cert_data.get("serial_no")
                        encrypt_certificate = cert_data.get("encrypt_certificate", {})

                        # 解密证书
                        cert_pem = self._decrypt_certificate(
                            encrypt_certificate.get("ciphertext"),
                            encrypt_certificate.get("nonce"),
                            encrypt_certificate.get("associated_data")
                        )

                        if cert_pem:
                            await self._cache_certificate(serial_no, cert_pem)

                    logger.info(f"Downloaded {len(certificates)} platform certificates")

        except Exception as e:
            logger.error(f"Error downloading certificates: {e}")

    def _decrypt_certificate(
        self,
        ciphertext: str,
        nonce: str,
        associated_data: str
    ) -> Optional[str]:
        """
        解密证书内容

        Args:
            ciphertext: 加密的密文(Base64)
            nonce: 随机串
            associated_data: 附加数据

        Returns:
            解密后的证书PEM字符串
        """
        try:
            key = self.api_v3_key.encode('utf-8')
            nonce_bytes = nonce.encode('utf-8')
            ciphertext_bytes = base64.b64decode(ciphertext)
            associated_data_bytes = associated_data.encode('utf-8') if associated_data else b""

            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce_bytes, ciphertext_bytes, associated_data_bytes)

            return plaintext.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to decrypt certificate: {e}")
            return None

    async def _cache_certificate(self, serial_no: str, cert_pem: str) -> None:
        """
        缓存证书

        Args:
            serial_no: 证书序列号
            cert_pem: 证书PEM字符串
        """
        try:
            # 解析证书
            cert = x509.load_pem_x509_certificate(
                cert_pem.encode('utf-8'),
                default_backend()
            )

            # 内存缓存
            expire_time = datetime.utcnow() + timedelta(seconds=self.CACHE_TTL_SECONDS)
            self._cert_cache[serial_no] = (cert, expire_time)

            # Redis缓存(如果可用)
            if self.redis_client:
                try:
                    cache_key = f"wechat_cert:{serial_no}"
                    await self.redis_client.setex(
                        cache_key,
                        self.CACHE_TTL_SECONDS,
                        cert_pem
                    )
                except Exception as e:
                    logger.warning(f"Failed to cache certificate in Redis: {e}")

            logger.info(f"Cached certificate: {serial_no}")

        except Exception as e:
            logger.error(f"Failed to cache certificate: {e}")

    def verify_signature(
        self,
        timestamp: str,
        nonce: str,
        body: str,
        signature: str,
        certificate: x509.Certificate
    ) -> bool:
        """
        验证微信回调签名

        Args:
            timestamp: 时间戳
            nonce: 随机串
            body: 请求体
            signature: 签名(Base64)
            certificate: 平台证书

        Returns:
            签名是否有效
        """
        try:
            # 构造验签串
            sign_str = f"{timestamp}\n{nonce}\n{body}\n"

            # 获取证书公钥
            public_key = certificate.public_key()

            # 解码签名
            signature_bytes = base64.b64decode(signature)

            # 验证签名
            public_key.verify(
                signature_bytes,
                sign_str.encode('utf-8'),
                padding.PKCS1v15(),
                hashes.SHA256()
            )

            return True

        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False


class WechatPayClient:
    """微信支付客户端(API v3)"""

    BASE_URL = "https://api.mch.weixin.qq.com"

    def __init__(self, config: WechatPayConfig, redis_client=None):
        self.app_id = config.app_id
        self.mch_id = config.mch_id
        self.api_v3_key = config.api_v3_key
        self.serial_no = config.serial_no
        self.notify_url = config.notify_url

        # 加载商户私钥
        self.private_key = self._load_private_key(config.private_key_path)

        # 初始化证书管理器
        self.cert_manager = WechatCertificateManager(
            mch_id=self.mch_id,
            api_v3_key=self.api_v3_key,
            private_key=self.private_key,
            serial_no=self.serial_no,
            redis_client=redis_client
        )

    # ===== Native支付(扫码支付) =====

    async def create_native_order(
        self,
        order_number: str,
        amount: int,
        description: str,
        attach: Optional[str] = None,
        time_expire: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建Native支付订单(扫码支付)

        Args:
            order_number: 商户订单号(唯一)
            amount: 订单金额(单位:分)
            description: 商品描述
            attach: 附加数据(可选,支付回调时原样返回)
            time_expire: 订单失效时间(格式: RFC3339, 可选)

        Returns:
            {
                "code_url": "weixin://wxpay/bizpayurl?pr=abc123"  # 二维码链接
            }

        Example:
            result = await client.create_native_order(
                order_number="ORDER_20260206_001",
                amount=9900,  # 99.00元
                description="基础套餐订阅",
                attach='{"tenant_id": "xxx"}'
            )
            qr_code_url = result["code_url"]  # 生成二维码
        """
        url = f"{self.BASE_URL}/v3/pay/transactions/native"

        data = {
            "appid": self.app_id,
            "mchid": self.mch_id,
            "description": description,
            "out_trade_no": order_number,
            "notify_url": self.notify_url,
            "amount": {
                "total": amount,
                "currency": "CNY"
            }
        }

        if attach:
            data["attach"] = attach

        if time_expire:
            data["time_expire"] = time_expire

        response = await self._request("POST", url, data)
        return response

    # ===== JSAPI支付(公众号/小程序) =====

    async def create_jsapi_order(
        self,
        order_number: str,
        amount: int,
        description: str,
        openid: str,
        attach: Optional[str] = None,
        time_expire: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建JSAPI支付订单(公众号/小程序支付)

        Args:
            order_number: 商户订单号
            amount: 订单金额(单位:分)
            description: 商品描述
            openid: 用户在商户appid下的唯一标识
            attach: 附加数据(可选)
            time_expire: 订单失效时间(可选)

        Returns:
            {
                "appId": "wx...",
                "timeStamp": "1234567890",
                "nonceStr": "abc123",
                "package": "prepay_id=wx...",
                "signType": "RSA",
                "paySign": "签名"
            }
            # 前端可直接使用这些参数调起微信支付

        Example:
            result = await client.create_jsapi_order(
                order_number="ORDER_20260206_002",
                amount=29900,  # 299.00元
                description="专业套餐订阅",
                openid="oUpF8uMuAJO_M2pxb1Q9zNjWeS6o"
            )
            # 将result返回给前端,前端调用wx.requestPayment(result)
        """
        url = f"{self.BASE_URL}/v3/pay/transactions/jsapi"

        data = {
            "appid": self.app_id,
            "mchid": self.mch_id,
            "description": description,
            "out_trade_no": order_number,
            "notify_url": self.notify_url,
            "amount": {
                "total": amount,
                "currency": "CNY"
            },
            "payer": {
                "openid": openid
            }
        }

        if attach:
            data["attach"] = attach

        if time_expire:
            data["time_expire"] = time_expire

        response = await self._request("POST", url, data)

        # 获取prepay_id并生成前端调起支付的参数
        prepay_id = response.get("prepay_id")
        if not prepay_id:
            raise ValueError("未获取到prepay_id")

        return self._generate_jsapi_params(prepay_id)

    # ===== 订单查询 =====

    async def query_order(self, order_number: str) -> Dict[str, Any]:
        """
        查询订单状态

        Args:
            order_number: 商户订单号

        Returns:
            {
                "out_trade_no": "ORDER_xxx",
                "transaction_id": "微信支付订单号",
                "trade_state": "SUCCESS",  # SUCCESS/REFUND/NOTPAY/CLOSED/REVOKED/USERPAYING/PAYERROR
                "trade_state_desc": "支付成功",
                "amount": {
                    "total": 9900,
                    "payer_total": 9900,
                    "currency": "CNY"
                },
                "payer": {
                    "openid": "oUpF8xxx"
                },
                "success_time": "2026-02-06T10:00:00+08:00"
            }
        """
        url = f"{self.BASE_URL}/v3/pay/transactions/out-trade-no/{order_number}"
        params = {"mchid": self.mch_id}
        return await self._request("GET", url, params=params)

    # ===== 关闭订单 =====

    async def close_order(self, order_number: str) -> bool:
        """
        关闭订单

        Args:
            order_number: 商户订单号

        Returns:
            bool: 是否成功关闭

        Note:
            - 订单生成后不能立即调用关单接口,最短调用时间间隔为5分钟
            - 订单关闭后,用户无法继续支付
        """
        url = f"{self.BASE_URL}/v3/pay/transactions/out-trade-no/{order_number}/close"
        data = {"mchid": self.mch_id}

        try:
            await self._request("POST", url, data)
            return True
        except Exception:
            return False

    # ===== 退款 =====

    async def refund(
        self,
        order_number: str,
        refund_number: str,
        amount: int,
        total_amount: int,
        reason: Optional[str] = None,
        notify_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        申请退款

        Args:
            order_number: 商户订单号
            refund_number: 商户退款单号(唯一)
            amount: 退款金额(单位:分)
            total_amount: 原订单金额(单位:分)
            reason: 退款原因(可选)
            notify_url: 退款结果通知URL(可选,默认使用配置的notify_url)

        Returns:
            {
                "refund_id": "微信退款单号",
                "out_refund_no": "商户退款单号",
                "transaction_id": "微信支付订单号",
                "out_trade_no": "商户订单号",
                "status": "SUCCESS",  # SUCCESS/CLOSED/PROCESSING/ABNORMAL
                "amount": {
                    "refund": 9900,
                    "total": 9900,
                    "currency": "CNY"
                }
            }

        Example:
            result = await client.refund(
                order_number="ORDER_20260206_001",
                refund_number="REFUND_20260206_001",
                amount=9900,
                total_amount=9900,
                reason="用户申请退款"
            )
        """
        url = f"{self.BASE_URL}/v3/refund/domestic/refunds"

        data = {
            "out_trade_no": order_number,
            "out_refund_no": refund_number,
            "reason": reason or "用户申请退款",
            "notify_url": notify_url or self.notify_url,
            "amount": {
                "refund": amount,
                "total": total_amount,
                "currency": "CNY"
            }
        }

        return await self._request("POST", url, data)

    async def query_refund(self, refund_number: str) -> Dict[str, Any]:
        """
        查询退款状态

        Args:
            refund_number: 商户退款单号

        Returns:
            退款详情
        """
        url = f"{self.BASE_URL}/v3/refund/domestic/refunds/{refund_number}"
        return await self._request("GET", url)

    # ===== 回调通知验证 =====

    async def verify_notification(self, headers: Dict[str, str], body: str) -> Dict[str, Any]:
        """
        验证回调通知签名并解密

        Args:
            headers: 请求头字典
            body: 请求体(JSON字符串)

        Returns:
            解密后的通知内容

        Example:
            @router.post("/webhook/wechat-pay")
            async def wechat_pay_callback(request: Request):
                headers = dict(request.headers)
                body = await request.body()

                try:
                    data = await wechat_client.verify_notification(headers, body.decode())
                    # 处理支付结果
                    if data["trade_state"] == "SUCCESS":
                        # 更新订单状态
                        pass
                    return {"code": "SUCCESS", "message": "成功"}
                except ValueError as e:
                    return {"code": "FAIL", "message": str(e)}

        Raises:
            ValueError: 签名验证失败
        """
        # 获取签名相关header(处理大小写不敏感)
        headers_lower = {k.lower(): v for k, v in headers.items()}
        timestamp = headers_lower.get("wechatpay-timestamp")
        nonce = headers_lower.get("wechatpay-nonce")
        signature = headers_lower.get("wechatpay-signature")
        serial = headers_lower.get("wechatpay-serial")

        if not all([timestamp, nonce, signature, serial]):
            raise ValueError("缺少必要的签名参数")

        # 1. 验证时间戳(防止重放攻击,允许5分钟误差)
        try:
            request_time = int(timestamp)
            current_time = int(time.time())
            if abs(current_time - request_time) > 300:
                raise ValueError("请求时间戳已过期")
        except ValueError as e:
            if "请求时间戳已过期" in str(e):
                raise
            raise ValueError("无效的时间戳格式")

        # 2. 获取平台证书
        certificate = await self.cert_manager.get_certificate(serial)
        if not certificate:
            raise ValueError(f"未找到对应的平台证书: {serial}")

        # 3. 验证签名
        if not self.cert_manager.verify_signature(
            timestamp=timestamp,
            nonce=nonce,
            body=body,
            signature=signature,
            certificate=certificate
        ):
            raise ValueError("签名验证失败")

        logger.info(f"WeChat notification signature verified successfully")

        # 4. 解密数据
        try:
            data = json.loads(body)
            resource = data.get("resource", {})

            decrypted = self._decrypt_resource(
                resource.get("ciphertext"),
                resource.get("nonce"),
                resource.get("associated_data")
            )

            return json.loads(decrypted)
        except Exception as e:
            raise ValueError(f"解密失败: {str(e)}")

    def verify_notification_sync(self, headers: Dict[str, str], body: str) -> Dict[str, Any]:
        """
        同步版本的回调验证(仅解密,跳过签名验证)

        警告: 此方法仅用于开发测试,生产环境请使用 verify_notification

        Args:
            headers: 请求头字典
            body: 请求体(JSON字符串)

        Returns:
            解密后的通知内容
        """
        logger.warning("Using sync verification without signature check - NOT for production!")

        # 获取签名相关header
        headers_lower = {k.lower(): v for k, v in headers.items()}
        timestamp = headers_lower.get("wechatpay-timestamp")
        nonce = headers_lower.get("wechatpay-nonce")
        signature = headers_lower.get("wechatpay-signature")
        serial = headers_lower.get("wechatpay-serial")

        if not all([timestamp, nonce, signature, serial]):
            raise ValueError("缺少必要的签名参数")

        # 解密数据
        try:
            data = json.loads(body)
            resource = data.get("resource", {})

            decrypted = self._decrypt_resource(
                resource.get("ciphertext"),
                resource.get("nonce"),
                resource.get("associated_data")
            )

            return json.loads(decrypted)
        except Exception as e:
            raise ValueError(f"解密失败: {str(e)}")

    # ===== 私有方法 =====

    async def _request(
        self,
        method: str,
        url: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        发送HTTP请求

        Args:
            method: 请求方法(GET/POST)
            url: 请求URL
            data: 请求体数据(POST)
            params: 查询参数(GET)

        Returns:
            响应数据
        """
        import aiohttp

        timestamp = int(time.time())
        nonce = str(uuid.uuid4()).replace("-", "")
        body = json.dumps(data) if data else ""

        # 生成签名
        signature = self._generate_signature(method, url, timestamp, nonce, body)

        # 构造Authorization头
        auth_header = (
            f'WECHATPAY2-SHA256-RSA2048 '
            f'mchid="{self.mch_id}",'
            f'nonce_str="{nonce}",'
            f'timestamp="{timestamp}",'
            f'serial_no="{self.serial_no}",'
            f'signature="{signature}"'
        )

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": auth_header,
            "User-Agent": "EcomChatBot/1.0"
        }

        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status not in [200, 204]:
                        error_text = await resp.text()
                        raise Exception(f"微信支付请求失败: {resp.status} - {error_text}")
                    if resp.status == 204:
                        return {}
                    return await resp.json()
            else:  # POST
                async with session.post(url, headers=headers, data=body) as resp:
                    if resp.status not in [200, 204]:
                        error_text = await resp.text()
                        raise Exception(f"微信支付请求失败: {resp.status} - {error_text}")
                    if resp.status == 204:
                        return {}
                    return await resp.json()

    def _generate_signature(
        self,
        method: str,
        url: str,
        timestamp: int,
        nonce: str,
        body: str
    ) -> str:
        """
        生成请求签名

        Args:
            method: HTTP方法
            url: 请求URL
            timestamp: 时间戳
            nonce: 随机字符串
            body: 请求体

        Returns:
            Base64编码的签名
        """
        from urllib.parse import urlparse
        import base64

        # 解析URL获取路径和查询参数
        parsed = urlparse(url)
        path = parsed.path
        if parsed.query:
            path = f"{path}?{parsed.query}"

        # 构造签名串
        sign_str = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body}\n"

        # 使用商户私钥签名
        signature_bytes = self.private_key.sign(
            sign_str.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )

        # Base64编码
        return base64.b64encode(signature_bytes).decode('utf-8')

    def _decrypt_resource(
        self,
        ciphertext: str,
        nonce: str,
        associated_data: str
    ) -> str:
        """
        解密回调数据

        Args:
            ciphertext: 加密的密文(Base64)
            nonce: 随机串
            associated_data: 附加数据

        Returns:
            解密后的明文
        """
        import base64

        # APIv3密钥
        key = self.api_v3_key.encode('utf-8')
        nonce_bytes = nonce.encode('utf-8')
        ciphertext_bytes = base64.b64decode(ciphertext)
        associated_data_bytes = associated_data.encode('utf-8') if associated_data else b""

        # 使用AES-256-GCM解密
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce_bytes, ciphertext_bytes, associated_data_bytes)

        return plaintext.decode('utf-8')

    def _generate_jsapi_params(self, prepay_id: str) -> Dict[str, str]:
        """
        生成JSAPI调起支付参数

        Args:
            prepay_id: 预支付交易会话标识

        Returns:
            前端调起支付所需参数
        """
        import base64

        timestamp = str(int(time.time()))
        nonce = str(uuid.uuid4()).replace("-", "")
        package = f"prepay_id={prepay_id}"

        # 构造签名串
        sign_str = f"{self.app_id}\n{timestamp}\n{nonce}\n{package}\n"

        # 签名
        signature_bytes = self.private_key.sign(
            sign_str.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        pay_sign = base64.b64encode(signature_bytes).decode('utf-8')

        return {
            "appId": self.app_id,
            "timeStamp": timestamp,
            "nonceStr": nonce,
            "package": package,
            "signType": "RSA",
            "paySign": pay_sign
        }

    def _load_private_key(self, private_key_path: str):
        """
        加载商户私钥

        Args:
            private_key_path: 私钥文件路径

        Returns:
            RSA私钥对象
        """
        try:
            with open(private_key_path, 'rb') as f:
                private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
            return private_key
        except FileNotFoundError:
            raise ValueError(f"私钥文件不存在: {private_key_path}")
        except Exception as e:
            raise ValueError(f"加载私钥失败: {str(e)}")


# ===== 工具函数 =====

def generate_order_number(prefix: str = "WX") -> str:
    """
    生成订单号

    Args:
        prefix: 订单号前缀

    Returns:
        格式: {prefix}_{YYYYMMDDHHMMSS}_{随机6位}
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = str(uuid.uuid4().hex)[:6].upper()
    return f"{prefix}_{timestamp}_{random_str}"


def yuan_to_fen(yuan: float) -> int:
    """
    元转分

    Args:
        yuan: 金额(元)

    Returns:
        金额(分)
    """
    return int(yuan * 100)


def fen_to_yuan(fen: int) -> float:
    """
    分转元

    Args:
        fen: 金额(分)

    Returns:
        金额(元)
    """
    return fen / 100