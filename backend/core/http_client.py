"""
共享 httpx.AsyncClient — 避免每次请求新建 TCP 连接

使用方式：
    from core.http_client import get_http_client

    client = get_http_client()
    resp = await client.post(url, ...)
"""
import httpx

_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """返回全局共享的 AsyncClient，按需创建。"""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
    return _client


async def close_http_client() -> None:
    """应用关闭时调用，优雅关闭连接池。"""
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
    _client = None
