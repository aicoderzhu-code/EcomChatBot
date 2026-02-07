"""
实时指标收集服务 - 基于Redis
"""
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import redis.asyncio as redis
import json


@dataclass
class MetricPoint:
    """指标数据点"""

    timestamp: datetime
    value: float
    labels: Dict[str, str] = None


class MetricsService:
    """指标收集服务"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    # ==================== 响应时间指标 ====================

    async def record_response_time(
        self,
        tenant_id: str,
        conversation_id: str,
        response_time_ms: int,
        endpoint: str = "chat",
    ):
        """记录响应时间"""
        today = datetime.utcnow().strftime("%Y%m%d")

        # 租户级别
        tenant_key = f"metrics:response_time:{tenant_id}:{today}"
        await self.redis.lpush(tenant_key, response_time_ms)
        await self.redis.expire(tenant_key, 86400 * 30)  # 30天

        # 全局级别
        global_key = f"metrics:response_time:global:{today}"
        await self.redis.lpush(global_key, response_time_ms)
        await self.redis.expire(global_key, 86400 * 7)  # 7天

        # 更新实时平均值
        await self._update_realtime_avg("response_time", tenant_id, response_time_ms)

    async def get_response_time_stats(
        self, tenant_id: Optional[str] = None, date: Optional[str] = None
    ) -> dict:
        """获取响应时间统计"""
        if date is None:
            date = datetime.utcnow().strftime("%Y%m%d")

        if tenant_id:
            key = f"metrics:response_time:{tenant_id}:{date}"
        else:
            key = f"metrics:response_time:global:{date}"

        times = await self.redis.lrange(key, 0, -1)
        if not times:
            return {"p50": 0, "p95": 0, "p99": 0, "avg": 0, "count": 0}

        times = sorted([int(t) for t in times])
        count = len(times)

        return {
            "p50": self._percentile(times, 50),
            "p95": self._percentile(times, 95),
            "p99": self._percentile(times, 99),
            "avg": sum(times) / count,
            "min": times[0],
            "max": times[-1],
            "count": count,
        }

    # ==================== 对话指标 ====================

    async def record_conversation_start(self, tenant_id: str, conversation_id: str):
        """记录对话开始"""
        today = datetime.utcnow().strftime("%Y%m%d")

        # 增加对话计数
        count_key = f"metrics:conversations:{tenant_id}:{today}"
        await self.redis.incr(count_key)
        await self.redis.expire(count_key, 86400 * 30)

        # 记录活跃会话
        active_key = f"metrics:active_conversations:{tenant_id}"
        await self.redis.sadd(active_key, conversation_id)
        await self.redis.expire(active_key, 86400)

    async def record_conversation_end(
        self,
        tenant_id: str,
        conversation_id: str,
        resolved: bool,
        transferred_to_human: bool = False,
    ):
        """记录对话结束"""
        today = datetime.utcnow().strftime("%Y%m%d")

        # 移除活跃会话
        active_key = f"metrics:active_conversations:{tenant_id}"
        await self.redis.srem(active_key, conversation_id)

        # 统计解决情况
        if resolved:
            resolved_key = f"metrics:resolved:{tenant_id}:{today}"
            await self.redis.incr(resolved_key)
            await self.redis.expire(resolved_key, 86400 * 30)

        if transferred_to_human:
            transfer_key = f"metrics:human_transfer:{tenant_id}:{today}"
            await self.redis.incr(transfer_key)
            await self.redis.expire(transfer_key, 86400 * 30)

    async def get_conversation_stats(
        self, tenant_id: str, date: Optional[str] = None
    ) -> dict:
        """获取对话统计"""
        if date is None:
            date = datetime.utcnow().strftime("%Y%m%d")

        total = int(
            await self.redis.get(f"metrics:conversations:{tenant_id}:{date}") or 0
        )
        resolved = int(
            await self.redis.get(f"metrics:resolved:{tenant_id}:{date}") or 0
        )
        transferred = int(
            await self.redis.get(f"metrics:human_transfer:{tenant_id}:{date}") or 0
        )
        active = await self.redis.scard(f"metrics:active_conversations:{tenant_id}")

        return {
            "total": total,
            "resolved": resolved,
            "transferred_to_human": transferred,
            "active": active,
            "resolution_rate": round(resolved / total * 100, 2) if total > 0 else 0,
            "transfer_rate": round(transferred / total * 100, 2) if total > 0 else 0,
        }

    # ==================== 满意度指标 ====================

    async def record_feedback(
        self,
        tenant_id: str,
        conversation_id: str,
        rating: int,  # 1-5
        comment: Optional[str] = None,
    ):
        """记录用户反馈"""
        today = datetime.utcnow().strftime("%Y%m%d")

        # 记录评分
        rating_key = f"metrics:ratings:{tenant_id}:{today}"
        await self.redis.lpush(rating_key, rating)
        await self.redis.expire(rating_key, 86400 * 30)

        # 记录评分分布
        dist_key = f"metrics:rating_dist:{tenant_id}:{today}"
        await self.redis.hincrby(dist_key, str(rating), 1)
        await self.redis.expire(dist_key, 86400 * 30)

    async def get_satisfaction_stats(
        self, tenant_id: str, date: Optional[str] = None
    ) -> dict:
        """获取满意度统计"""
        if date is None:
            date = datetime.utcnow().strftime("%Y%m%d")

        ratings_key = f"metrics:ratings:{tenant_id}:{date}"
        ratings = await self.redis.lrange(ratings_key, 0, -1)

        if not ratings:
            return {"avg_rating": 0, "nps": 0, "distribution": {}, "count": 0}

        ratings = [int(r) for r in ratings]
        count = len(ratings)
        avg = sum(ratings) / count

        # 获取分布
        dist_key = f"metrics:rating_dist:{tenant_id}:{date}"
        distribution = await self.redis.hgetall(dist_key)
        distribution = {k.decode(): int(v) for k, v in distribution.items()}

        # 计算NPS (Net Promoter Score)
        # 5分为推荐者,4分为中立,1-3分为贬低者
        promoters = distribution.get("5", 0)
        detractors = sum(distribution.get(str(i), 0) for i in range(1, 4))
        nps = round((promoters - detractors) / count * 100, 2) if count > 0 else 0

        return {
            "avg_rating": round(avg, 2),
            "nps": nps,
            "distribution": distribution,
            "count": count,
        }

    # ==================== Token使用指标 ====================

    async def record_token_usage(
        self,
        tenant_id: str,
        conversation_id: str,
        input_tokens: int,
        output_tokens: int,
        model: str = "default",
    ):
        """记录Token使用"""
        today = datetime.utcnow().strftime("%Y%m%d")

        # 租户级别
        tenant_key = f"metrics:tokens:{tenant_id}:{today}"
        await self.redis.hincrby(tenant_key, "input", input_tokens)
        await self.redis.hincrby(tenant_key, "output", output_tokens)
        await self.redis.expire(tenant_key, 86400 * 30)

        # 模型级别
        model_key = f"metrics:tokens_by_model:{tenant_id}:{model}:{today}"
        await self.redis.hincrby(model_key, "input", input_tokens)
        await self.redis.hincrby(model_key, "output", output_tokens)
        await self.redis.expire(model_key, 86400 * 30)

    async def get_token_stats(
        self, tenant_id: str, date: Optional[str] = None
    ) -> dict:
        """获取Token使用统计"""
        if date is None:
            date = datetime.utcnow().strftime("%Y%m%d")

        tenant_key = f"metrics:tokens:{tenant_id}:{date}"
        token_data = await self.redis.hgetall(tenant_key)

        if not token_data:
            return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

        input_tokens = int(token_data.get(b"input", 0))
        output_tokens = int(token_data.get(b"output", 0))

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }

    # ==================== 辅助方法 ====================

    async def _update_realtime_avg(
        self, metric_name: str, tenant_id: str, value: float
    ):
        """更新实时平均值(滑动窗口)"""
        key = f"metrics:realtime:{metric_name}:{tenant_id}"

        # 使用有序集合,score为时间戳
        now = time.time()
        window = 300  # 5分钟窗口

        pipe = self.redis.pipeline()
        # 移除窗口外数据
        pipe.zremrangebyscore(key, 0, now - window)
        # 添加新数据
        pipe.zadd(key, {f"{now}:{value}": now})
        # 设置过期
        pipe.expire(key, window * 2)
        await pipe.execute()

    async def get_realtime_avg(
        self, metric_name: str, tenant_id: str, window: int = 300
    ) -> float:
        """获取实时平均值"""
        key = f"metrics:realtime:{metric_name}:{tenant_id}"

        now = time.time()
        window_start = now - window

        # 获取窗口内的所有数据
        data = await self.redis.zrangebyscore(key, window_start, now, withscores=True)

        if not data:
            return 0.0

        # 解析数据并计算平均值
        values = [float(item[0].decode().split(":")[1]) for item in data]
        return sum(values) / len(values) if values else 0.0

    def _percentile(self, sorted_data: List[int], percentile: int) -> int:
        """计算百分位数"""
        if not sorted_data:
            return 0
        k = (len(sorted_data) - 1) * percentile / 100
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_data) else f
        return int(sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f]))

    # ==================== 聚合查询 ====================

    async def get_dashboard_metrics(
        self, tenant_id: Optional[str] = None
    ) -> dict:
        """获取Dashboard指标"""
        today = datetime.utcnow().strftime("%Y%m%d")

        if tenant_id:
            response_stats = await self.get_response_time_stats(tenant_id, today)
            conversation_stats = await self.get_conversation_stats(tenant_id, today)
            satisfaction_stats = await self.get_satisfaction_stats(tenant_id, today)
            token_stats = await self.get_token_stats(tenant_id, today)

            # 获取实时平均响应时间
            realtime_avg_response = await self.get_realtime_avg(
                "response_time", tenant_id
            )
        else:
            # 全局统计
            response_stats = await self.get_response_time_stats(None, today)
            conversation_stats = {
                "total": 0,
                "resolved": 0,
                "active": 0,
            }  # 需要聚合
            satisfaction_stats = {"avg_rating": 0, "nps": 0}  # 需要聚合
            token_stats = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
            realtime_avg_response = 0

        return {
            "response_time": response_stats,
            "conversations": conversation_stats,
            "satisfaction": satisfaction_stats,
            "tokens": token_stats,
            "realtime": {
                "avg_response_time_5min": round(realtime_avg_response, 2),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    # ==================== 趋势数据 ====================

    async def get_trend_data(
        self, tenant_id: str, metric: str, days: int = 7
    ) -> List[dict]:
        """
        获取趋势数据

        Args:
            tenant_id: 租户ID
            metric: 指标名称 (conversations/resolved/ratings)
            days: 天数

        Returns:
            [{"date": "20240101", "value": 123}, ...]
        """
        results = []
        today = datetime.utcnow()

        for i in range(days):
            date = (today - timedelta(days=i)).strftime("%Y%m%d")

            if metric == "conversations":
                key = f"metrics:conversations:{tenant_id}:{date}"
                value = int(await self.redis.get(key) or 0)
            elif metric == "resolved":
                key = f"metrics:resolved:{tenant_id}:{date}"
                value = int(await self.redis.get(key) or 0)
            elif metric == "ratings":
                ratings = await self.get_satisfaction_stats(tenant_id, date)
                value = ratings["avg_rating"]
            else:
                value = 0

            results.append(
                {
                    "date": date,
                    "value": value,
                }
            )

        # 反转列表，从早到晚
        results.reverse()
        return results
