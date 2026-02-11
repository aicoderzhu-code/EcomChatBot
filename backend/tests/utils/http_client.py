"""
HTTP 客户端封装
"""
import asyncio
import httpx
from typing import Optional, Dict, Any
from rich.console import Console

console = Console()

# 可重试的瞬时网络错误
RETRYABLE_EXCEPTIONS = (
    httpx.ReadError,
    httpx.RemoteProtocolError,
    httpx.ConnectError,
    httpx.PoolTimeout,
    ConnectionError,
)


class APIClient:
    """真实HTTP请求客户端"""

    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
        self.api_key: Optional[str] = None
        self.jwt_token: Optional[str] = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        # 禁用代理，直接连接本地服务
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            proxies=None,  # 禁用所有代理
            trust_env=False,  # 不从环境变量读取代理配置
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()

    def set_api_key(self, api_key: str):
        """设置API Key"""
        self.api_key = api_key
        console.print(f"[green]✓ API Key已设置: {api_key[:20]}...[/green]")

    def set_jwt_token(self, token: str):
        """设置JWT Token"""
        self.jwt_token = token
        console.print(f"[green]✓ JWT Token已设置: {token[:20]}...[/green]")

    def clear_auth(self):
        """清除认证信息"""
        self.api_key = None
        self.jwt_token = None
        console.print("[yellow]⚠ 认证信息已清除[/yellow]")

    def _get_headers(self, extra_headers: Optional[Dict] = None) -> Dict:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}

        if self.api_key:
            headers["X-API-Key"] = self.api_key
        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"

        if extra_headers:
            headers.update(extra_headers)

        return headers

    async def request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> httpx.Response:
        """统一请求方法，对瞬时网络错误自动重试"""
        if not self.client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers(kwargs.pop("headers", None))
        max_retries = 3
        retry_delay = 0.5

        for attempt in range(max_retries):
            try:
                console.print(f"[blue]→ {method} {endpoint}[/blue]")
                response = await self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    **kwargs
                )
                status_color = "green" if response.status_code < 400 else "red"
                console.print(f"[{status_color}]← {response.status_code}[/{status_color}]")
                return response

            except RETRYABLE_EXCEPTIONS as e:
                if attempt < max_retries - 1:
                    console.print(f"[yellow]⚠ 网络错误(重试 {attempt + 1}/{max_retries}): {e}[/yellow]")
                    await asyncio.sleep(retry_delay * (attempt + 1))
                else:
                    console.print(f"[red]✗ 请求失败(已重试{max_retries}次): {e}[/red]")
                    raise
            except httpx.TimeoutException:
                console.print("[red]✗ 请求超时[/red]")
                raise
            except Exception as e:
                console.print(f"[red]✗ 请求失败: {str(e)}[/red]")
                raise

    async def get(self, endpoint: str, **kwargs) -> httpx.Response:
        """GET 请求"""
        return await self.request("GET", endpoint, **kwargs)

    async def post(self, endpoint: str, **kwargs) -> httpx.Response:
        """POST 请求"""
        return await self.request("POST", endpoint, **kwargs)

    async def put(self, endpoint: str, **kwargs) -> httpx.Response:
        """PUT 请求"""
        return await self.request("PUT", endpoint, **kwargs)

    async def delete(self, endpoint: str, **kwargs) -> httpx.Response:
        """DELETE 请求"""
        return await self.request("DELETE", endpoint, **kwargs)

    async def close(self):
        """关闭客户端"""
        if self.client:
            await self.client.aclose()
            self.client = None
