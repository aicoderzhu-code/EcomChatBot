"""
监控服务 - 实时监控统计
"""
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.conversation import Conversation, Message
from core.exceptions import AppException


class MonitorService:
    """监控服务 - 提供实时监控统计API"""

    def __init__(self, db: AsyncSession, tenant_id: str | None = None):
        self.db = db
        self.tenant_id = tenant_id

    async def get_conversation_stats(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None
    ) -> dict[str, Any]:
        """
        获取对话统计

        Args:
            start_time: 开始时间（默认24小时前）
            end_time: 结束时间（默认当前时间）

        Returns:
            {
                "total_conversations": int,  # 总对话数
                "active_conversations": int,  # 活跃对话数
                "closed_conversations": int,  # 已关闭对话数
                "avg_messages_per_conversation": float,  # 平均每对话消息数
                "total_messages": int,  # 总消息数
                "total_tokens": int,  # 总Token消耗
            }
        """
        # 默认时间范围：最近24小时
        if not start_time:
            start_time = datetime.now() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.now()

        # 构建查询条件
        conditions = [
            Conversation.created_at >= start_time,
            Conversation.created_at <= end_time
        ]

        if self.tenant_id:
            conditions.append(Conversation.tenant_id == self.tenant_id)

        # 总对话数
        total_result = await self.db.execute(
            select(func.count(Conversation.id)).where(*conditions)
        )
        total_conversations = total_result.scalar() or 0

        # 活跃对话数
        active_result = await self.db.execute(
            select(func.count(Conversation.id)).where(
                *conditions,
                Conversation.status == "active"
            )
        )
        active_conversations = active_result.scalar() or 0

        # 已关闭对话数
        closed_result = await self.db.execute(
            select(func.count(Conversation.id)).where(
                *conditions,
                Conversation.status == "closed"
            )
        )
        closed_conversations = closed_result.scalar() or 0

        # 统计消息数和Token消耗
        message_conditions = [
            Message.created_at >= start_time,
            Message.created_at <= end_time
        ]

        if self.tenant_id:
            message_conditions.append(Message.tenant_id == self.tenant_id)

        # 总消息数
        total_messages_result = await self.db.execute(
            select(func.count(Message.id)).where(*message_conditions)
        )
        total_messages = total_messages_result.scalar() or 0

        # 总Token消耗
        tokens_result = await self.db.execute(
            select(
                func.sum(Message.input_tokens) + func.sum(Message.output_tokens)
            ).where(*message_conditions)
        )
        total_tokens = tokens_result.scalar() or 0

        # 平均每对话消息数
        avg_messages = (
            total_messages / total_conversations
            if total_conversations > 0
            else 0
        )

        return {
            "total_conversations": total_conversations,
            "active_conversations": active_conversations,
            "closed_conversations": closed_conversations,
            "avg_messages_per_conversation": round(avg_messages, 2),
            "total_messages": total_messages,
            "total_tokens": total_tokens,
        }

    async def get_response_time_stats(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None
    ) -> dict[str, Any]:
        """
        获取响应时间统计

        Returns:
            {
                "avg_response_time": float,  # 平均响应时间(ms)
                "min_response_time": int,  # 最小响应时间
                "max_response_time": int,  # 最大响应时间
                "p50_response_time": float,  # P50响应时间
                "p95_response_time": float,  # P95响应时间
                "p99_response_time": float,  # P99响应时间
            }
        """
        if not start_time:
            start_time = datetime.now() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.now()

        # 查询所有有响应时间的消息
        conditions = [
            Message.role == "assistant",
            Message.response_time.isnot(None),
            Message.created_at >= start_time,
            Message.created_at <= end_time
        ]

        if self.tenant_id:
            conditions.append(Message.tenant_id == self.tenant_id)

        # 获取所有响应时间
        result = await self.db.execute(
            select(Message.response_time).where(*conditions)
        )
        response_times = [row[0] for row in result.fetchall()]

        if not response_times:
            return {
                "avg_response_time": 0,
                "min_response_time": 0,
                "max_response_time": 0,
                "p50_response_time": 0,
                "p95_response_time": 0,
                "p99_response_time": 0,
            }

        # 计算统计数据
        avg_time = sum(response_times) / len(response_times)
        min_time = min(response_times)
        max_time = max(response_times)

        # 计算百分位数
        sorted_times = sorted(response_times)
        p50 = sorted_times[int(len(sorted_times) * 0.5)]
        p95 = sorted_times[int(len(sorted_times) * 0.95)]
        p99 = sorted_times[int(len(sorted_times) * 0.99)]

        return {
            "avg_response_time": round(avg_time, 2),
            "min_response_time": min_time,
            "max_response_time": max_time,
            "p50_response_time": p50,
            "p95_response_time": p95,
            "p99_response_time": p99,
        }

    async def get_satisfaction_stats(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None
    ) -> dict[str, Any]:
        """
        获取满意度统计

        Returns:
            {
                "avg_satisfaction": float,  # 平均满意度
                "total_ratings": int,  # 总评分次数
                "distribution": {  # 评分分布
                    "5": int,
                    "4": int,
                    "3": int,
                    "2": int,
                    "1": int,
                },
                "satisfaction_rate": float,  # 满意率（4-5分占比）
            }
        """
        if not start_time:
            start_time = datetime.now() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.now()

        # 查询所有有满意度评分的对话
        conditions = [
            Conversation.satisfaction_score.isnot(None),
            Conversation.created_at >= start_time,
            Conversation.created_at <= end_time
        ]

        if self.tenant_id:
            conditions.append(Conversation.tenant_id == self.tenant_id)

        # 获取所有评分
        result = await self.db.execute(
            select(Conversation.satisfaction_score).where(*conditions)
        )
        scores = [row[0] for row in result.fetchall()]

        if not scores:
            return {
                "avg_satisfaction": 0,
                "total_ratings": 0,
                "distribution": {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0},
                "satisfaction_rate": 0,
            }

        # 计算平均分
        avg_satisfaction = sum(scores) / len(scores)

        # 统计分布
        distribution = {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}
        for score in scores:
            distribution[str(score)] += 1

        # 计算满意率（4-5分占比）
        satisfaction_rate = (
            (distribution["5"] + distribution["4"]) / len(scores) * 100
            if len(scores) > 0
            else 0
        )

        return {
            "avg_satisfaction": round(avg_satisfaction, 2),
            "total_ratings": len(scores),
            "distribution": distribution,
            "satisfaction_rate": round(satisfaction_rate, 2),
        }

    async def get_dashboard_summary(
        self,
        time_range: str = "24h"
    ) -> dict[str, Any]:
        """
        获取Dashboard汇总数据

        Args:
            time_range: 时间范围 (24h/7d/30d)

        Returns:
            {
                "conversation_stats": dict,
                "response_time_stats": dict,
                "satisfaction_stats": dict,
                "time_range": str,
            }
        """
        # 计算时间范围
        now = datetime.now()
        if time_range == "24h":
            start_time = now - timedelta(hours=24)
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
        elif time_range == "30d":
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(hours=24)

        # 并行获取各项统计数据
        conversation_stats = await self.get_conversation_stats(start_time, now)
        response_time_stats = await self.get_response_time_stats(start_time, now)
        satisfaction_stats = await self.get_satisfaction_stats(start_time, now)

        return {
            "conversation_stats": conversation_stats,
            "response_time_stats": response_time_stats,
            "satisfaction_stats": satisfaction_stats,
            "time_range": time_range,
        }

    async def get_hourly_conversation_trend(
        self,
        hours: int = 24
    ) -> list[dict[str, Any]]:
        """
        获取每小时对话趋势

        Args:
            hours: 统计最近多少小时

        Returns:
            [
                {
                    "hour": str,  # "2024-01-01 10:00"
                    "conversations": int,
                    "messages": int,
                },
                ...
            ]
        """
        results = []
        now = datetime.now()

        for i in range(hours):
            hour_start = now - timedelta(hours=i+1)
            hour_end = now - timedelta(hours=i)

            # 统计该小时的对话数
            conv_conditions = [
                Conversation.created_at >= hour_start,
                Conversation.created_at < hour_end
            ]

            if self.tenant_id:
                conv_conditions.append(Conversation.tenant_id == self.tenant_id)

            conv_result = await self.db.execute(
                select(func.count(Conversation.id)).where(*conv_conditions)
            )
            conversations = conv_result.scalar() or 0

            # 统计该小时的消息数
            msg_conditions = [
                Message.created_at >= hour_start,
                Message.created_at < hour_end
            ]

            if self.tenant_id:
                msg_conditions.append(Message.tenant_id == self.tenant_id)

            msg_result = await self.db.execute(
                select(func.count(Message.id)).where(*msg_conditions)
            )
            messages = msg_result.scalar() or 0

            results.append({
                "hour": hour_start.strftime("%Y-%m-%d %H:00"),
                "conversations": conversations,
                "messages": messages,
            })

        # 反转列表，从早到晚
        results.reverse()

        return results
