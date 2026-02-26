"""
监控服务 - 实时监控统计
"""
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy import select, func, and_, case
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
                "resolved_conversations": int,  # 已解决对话数
                "transferred_to_human": int,  # 转人工对话数
                "resolution_rate": float,  # 解决率(%)
                "transfer_rate": float,  # 转人工率(%)
                "avg_resolution_time": float,  # 平均解决时长(秒)
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

        # 单次查询获取所有统计（7 个独立查询 → 1 个条件聚合）
        stats_result = await self.db.execute(
            select(
                func.count(Conversation.id).label("total"),
                func.count(case((Conversation.status == "active", 1))).label("active"),
                func.count(case((Conversation.status == "closed", 1))).label("closed"),
                func.count(case((Conversation.resolved == 1, 1))).label("resolved"),
                func.count(case((Conversation.transferred_to_human == 1, 1))).label("transferred"),
                func.avg(Conversation.resolution_time).label("avg_resolution_time"),
            ).where(*conditions)
        )
        row = stats_result.one()
        total_conversations = row.total or 0
        active_conversations = row.active or 0
        closed_conversations = row.closed or 0
        resolved_conversations = row.resolved or 0
        transferred_conversations = row.transferred or 0
        avg_resolution_time = row.avg_resolution_time or 0

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

        # 计算解决率和转人工率
        resolution_rate = (
            (resolved_conversations / total_conversations * 100)
            if total_conversations > 0
            else 0
        )

        transfer_rate = (
            (transferred_conversations / total_conversations * 100)
            if total_conversations > 0
            else 0
        )

        return {
            "total_conversations": total_conversations,
            "active_conversations": active_conversations,
            "closed_conversations": closed_conversations,
            "resolved_conversations": resolved_conversations,
            "transferred_to_human": transferred_conversations,
            "resolution_rate": round(resolution_rate, 2),
            "transfer_rate": round(transfer_rate, 2),
            "avg_resolution_time": round(avg_resolution_time, 2) if avg_resolution_time else 0,
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
        start_time = now - timedelta(hours=hours)

        # 对话趋势：GROUP BY 替代 N 次循环查询
        conv_conditions = [
            Conversation.created_at >= start_time,
            Conversation.created_at <= now,
        ]
        if self.tenant_id:
            conv_conditions.append(Conversation.tenant_id == self.tenant_id)

        conv_stmt = (
            select(
                func.date_trunc("hour", Conversation.created_at).label("hour"),
                func.count(Conversation.id).label("count"),
            )
            .where(*conv_conditions)
            .group_by("hour")
            .order_by("hour")
        )
        conv_result = await self.db.execute(conv_stmt)
        conv_by_hour = {row.hour: row.count for row in conv_result.all()}

        # 消息趋势：GROUP BY
        msg_conditions = [
            Message.created_at >= start_time,
            Message.created_at <= now,
        ]
        if self.tenant_id:
            msg_conditions.append(Message.tenant_id == self.tenant_id)

        msg_stmt = (
            select(
                func.date_trunc("hour", Message.created_at).label("hour"),
                func.count(Message.id).label("count"),
            )
            .where(*msg_conditions)
            .group_by("hour")
            .order_by("hour")
        )
        msg_result = await self.db.execute(msg_stmt)
        msg_by_hour = {row.hour: row.count for row in msg_result.all()}

        # 按小时填充结果（保持原有格式）
        for i in range(hours - 1, -1, -1):
            hour_start = (now - timedelta(hours=i + 1)).replace(minute=0, second=0, microsecond=0)
            results.append({
                "hour": hour_start.strftime("%Y-%m-%d %H:00"),
                "conversations": conv_by_hour.get(hour_start, 0),
                "messages": msg_by_hour.get(hour_start, 0),
            })

        return results

    async def mark_conversation_resolved(
        self,
        conversation_id: str,
        resolved: bool = True,
        resolution_type: str = "ai",
        transferred_to_human: bool = False,
        transfer_reason: str | None = None
    ):
        """
        标记对话解决状态

        Args:
            conversation_id: 对话ID
            resolved: 是否解决
            resolution_type: 解决方式(ai/human/timeout/abandoned)
            transferred_to_human: 是否转人工
            transfer_reason: 转人工原因
        """
        from models.conversation import Conversation

        # 查询对话
        result = await self.db.execute(
            select(Conversation).where(
                Conversation.conversation_id == conversation_id
            )
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise ValueError(f"对话不存在: {conversation_id}")

        # 更新解决状态
        conversation.resolved = resolved
        conversation.resolution_type = resolution_type
        conversation.transferred_to_human = transferred_to_human
        conversation.transfer_reason = transfer_reason

        # 计算解决时长（如果有开始时间）
        if conversation.start_time and resolved:
            conversation.resolution_time = int(
                (datetime.now() - conversation.start_time).total_seconds()
            )

        await self.db.commit()

    async def get_resolution_breakdown(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None
    ) -> dict[str, Any]:
        """
        获取解决方式分布

        Returns:
            {
                "by_type": {
                    "ai": int,  # AI解决数量
                    "human": int,  # 人工解决数量
                    "timeout": int,  # 超时未解决
                    "abandoned": int,  # 用户放弃
                },
                "transfer_reasons": {
                    "reason": count
                },
            }
        """
        if not start_time:
            start_time = datetime.now() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.now()

        from models.conversation import Conversation

        conditions = [
            Conversation.created_at >= start_time,
            Conversation.created_at <= end_time
        ]

        if self.tenant_id:
            conditions.append(Conversation.tenant_id == self.tenant_id)

        # 按解决方式统计
        by_type_result = await self.db.execute(
            select(
                Conversation.resolution_type,
                func.count(Conversation.id)
            )
            .where(
                *conditions,
                Conversation.resolution_type.isnot(None)
            )
            .group_by(Conversation.resolution_type)
        )

        by_type = {}
        for row in by_type_result.fetchall():
            by_type[row[0]] = row[1]

        # 转人工原因统计（transferred_to_human 是 INTEGER 类型）
        transfer_reasons_result = await self.db.execute(
            select(
                Conversation.transfer_reason,
                func.count(Conversation.id)
            )
            .where(
                *conditions,
                Conversation.transferred_to_human == 1,
                Conversation.transfer_reason.isnot(None)
            )
            .group_by(Conversation.transfer_reason)
        )

        transfer_reasons = {}
        for row in transfer_reasons_result.fetchall():
            transfer_reasons[row[0]] = row[1]

        return {
            "by_type": by_type,
            "transfer_reasons": transfer_reasons,
        }
