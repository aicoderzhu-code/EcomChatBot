"""
统一容错机制 — 重试 / 超时 / 断路器 / 降级

使用示例:

    from core.resilience import retry_async, CircuitBreaker, with_timeout, with_fallback

    # 1. 重试装饰器
    @retry_async(max_attempts=3, base_delay=1.0, max_delay=10.0)
    async def call_external_api():
        ...

    # 2. 断路器
    llm_breaker = CircuitBreaker("llm", failure_threshold=5, recovery_timeout=60)
    async with llm_breaker:
        result = await llm.ainvoke(...)

    # 3. 超时
    result = await with_timeout(coro, timeout=15.0, service_name="embedding")

    # 4. 降级
    result = await with_fallback(primary_coro, fallback_value, service_name="rerank")
"""
import asyncio
import functools
import logging
import time
from typing import Any, Callable, TypeVar

from core.exceptions import ExternalServiceException

logger = logging.getLogger(__name__)

T = TypeVar("T")

# ---------------------------------------------------------------------------
# 重试
# ---------------------------------------------------------------------------

# 默认可重试的异常类型
RETRIABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    OSError,
)


def retry_async(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retriable_exceptions: tuple[type[Exception], ...] | None = None,
    service_name: str = "",
):
    """异步函数指数退避重试装饰器

    Args:
        max_attempts: 最大重试次数（含首次调用）
        base_delay: 基础延迟秒数
        max_delay: 最大延迟秒数
        retriable_exceptions: 可重试的异常类型；None 使用默认列表
        service_name: 服务名称（用于日志）
    """
    retry_on = retriable_exceptions or RETRIABLE_EXCEPTIONS

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            name = service_name or func.__qualname__
            last_exc: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except retry_on as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        logger.error(
                            "[%s] 第 %d/%d 次调用失败，不再重试: %s",
                            name, attempt, max_attempts, exc,
                        )
                        raise
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    logger.warning(
                        "[%s] 第 %d/%d 次调用失败，%.1fs 后重试: %s",
                        name, attempt, max_attempts, delay, exc,
                    )
                    await asyncio.sleep(delay)

            # 理论上不可达，但兜底
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# 断路器（Circuit Breaker）
# ---------------------------------------------------------------------------

class CircuitBreakerOpen(ExternalServiceException):
    """断路器处于 OPEN 状态时抛出"""

    def __init__(self, service: str):
        super().__init__(service, f"断路器已打开，服务暂时不可用（将在恢复窗口后自动探测）")


class CircuitBreaker:
    """简易断路器

    状态流转: CLOSED → (连续失败 >= threshold) → OPEN → (recovery_timeout 后) → HALF_OPEN → (成功) → CLOSED
                                                                                    → (失败) → OPEN
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self._state = self.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> str:
        if self._state == self.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                return self.HALF_OPEN
        return self._state

    async def __aenter__(self):
        current = self.state
        if current == self.OPEN:
            raise CircuitBreakerOpen(self.service_name)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        async with self._lock:
            if exc_type is None:
                # 调用成功 → 重置
                self._failure_count = 0
                self._state = self.CLOSED
            else:
                self._failure_count += 1
                self._last_failure_time = time.monotonic()
                if self._failure_count >= self.failure_threshold:
                    self._state = self.OPEN
                    logger.error(
                        "[CircuitBreaker:%s] 连续失败 %d 次，断路器打开（%ds 后探测）",
                        self.service_name, self._failure_count, self.recovery_timeout,
                    )
        # 不吞异常，继续传播
        return False

    def reset(self):
        """手动重置断路器"""
        self._state = self.CLOSED
        self._failure_count = 0


# ---------------------------------------------------------------------------
# 超时
# ---------------------------------------------------------------------------

async def with_timeout(
    coro,
    timeout: float,
    service_name: str = "external",
) -> Any:
    """为异步调用添加超时

    Args:
        coro: 可等待对象
        timeout: 超时秒数
        service_name: 服务名称（用于错误信息）

    Raises:
        ExternalServiceException: 超时后抛出
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise ExternalServiceException(
            service_name, f"调用超时（{timeout}s）"
        )


# ---------------------------------------------------------------------------
# 降级
# ---------------------------------------------------------------------------

async def with_fallback(
    coro,
    fallback_value: T,
    service_name: str = "external",
) -> T:
    """带降级的异步调用：主调用失败时返回 fallback_value

    Args:
        coro: 可等待对象
        fallback_value: 降级返回值
        service_name: 服务名称（用于日志）

    Returns:
        正常结果或降级值
    """
    try:
        return await coro
    except Exception as exc:
        logger.warning(
            "[%s] 调用失败，降级处理: %s", service_name, exc,
        )
        return fallback_value
