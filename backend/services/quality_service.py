"""
对话质量评估服务
"""
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.conversation import Conversation, Message
from core.exceptions import AppException


class QualityService:
    """对话质量评估服务"""

    def __init__(self, db: AsyncSession, tenant_id: str | None = None):
        self.db = db
        self.tenant_id = tenant_id

    async def evaluate_conversation_quality(
        self,
        conversation_id: str
    ) -> dict[str, Any]:
        """
        评估单个对话的质量

        Args:
            conversation_id: 对话ID

        Returns:
            {
                "conversation_id": str,
                "quality_score": float,  # 总分 0-100
                "metrics": {
                    "response_time_score": float,  # 响应时间得分
                    "resolution_score": float,  # 解决率得分
                    "satisfaction_score": float,  # 满意度得分
                    "message_quality_score": float,  # 消息质量得分
                },
                "issues": list[str],  # 发现的问题
                "suggestions": list[str],  # 改进建议
            }
        """
        # 查询对话
        stmt = select(Conversation).where(
            Conversation.conversation_id == conversation_id
        )
        if self.tenant_id:
            stmt = stmt.where(Conversation.tenant_id == self.tenant_id)

        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise AppException("对话不存在")

        # 1. 评估响应时间
        response_time_score = await self._evaluate_response_time(conversation_id)

        # 2. 评估解决率
        resolution_score = await self._evaluate_resolution(conversation)

        # 3. 评估满意度
        satisfaction_score = await self._evaluate_satisfaction(conversation)

        # 4. 评估消息质量
        message_quality_score = await self._evaluate_message_quality(conversation_id)

        # 计算总分 (加权平均)
        weights = {
            "response_time": 0.25,
            "resolution": 0.30,
            "satisfaction": 0.30,
            "message_quality": 0.15,
        }

        quality_score = (
            response_time_score * weights["response_time"] +
            resolution_score * weights["resolution"] +
            satisfaction_score * weights["satisfaction"] +
            message_quality_score * weights["message_quality"]
        )

        # 生成问题和建议
        issues, suggestions = self._generate_feedback({
            "response_time": response_time_score,
            "resolution": resolution_score,
            "satisfaction": satisfaction_score,
            "message_quality": message_quality_score,
        })

        return {
            "conversation_id": conversation_id,
            "quality_score": round(quality_score, 2),
            "metrics": {
                "response_time_score": round(response_time_score, 2),
                "resolution_score": round(resolution_score, 2),
                "satisfaction_score": round(satisfaction_score, 2),
                "message_quality_score": round(message_quality_score, 2),
            },
            "issues": issues,
            "suggestions": suggestions,
        }

    async def _evaluate_response_time(self, conversation_id: str) -> float:
        """
        评估响应时间

        评分标准:
        - < 3秒: 100分
        - 3-5秒: 80分
        - 5-10秒: 60分
        - > 10秒: 40分
        """
        stmt = select(
            func.avg(Message.response_time)
        ).where(
            and_(
                Message.conversation_id == conversation_id,
                Message.role == "assistant",
                Message.response_time.isnot(None)
            )
        )
        result = await self.db.execute(stmt)
        avg_response_time = result.scalar() or 0

        if avg_response_time < 3000:  # < 3秒
            return 100.0
        elif avg_response_time < 5000:  # 3-5秒
            return 80.0
        elif avg_response_time < 10000:  # 5-10秒
            return 60.0
        else:  # > 10秒
            return 40.0

    async def _evaluate_resolution(self, conversation: Conversation) -> float:
        """
        评估解决率

        评分标准:
        - 状态为closed: 100分
        - 消息数 > 5: 80分
        - 消息数 3-5: 60分
        - 消息数 < 3: 40分
        """
        if conversation.status == "closed":
            return 100.0

        if conversation.message_count > 5:
            return 80.0
        elif conversation.message_count >= 3:
            return 60.0
        else:
            return 40.0

    async def _evaluate_satisfaction(self, conversation: Conversation) -> float:
        """
        评估满意度

        评分标准:
        - 5分: 100分
        - 4分: 80分
        - 3分: 60分
        - 2分: 40分
        - 1分: 20分
        - 未评分: 50分（中性）
        """
        if conversation.satisfaction_score is None:
            return 50.0

        return conversation.satisfaction_score * 20.0

    async def _evaluate_message_quality(self, conversation_id: str) -> float:
        """
        评估消息质量

        考虑因素:
        - 回复是否过短（< 20字符）
        - 是否包含错误信息
        - Token使用效率
        """
        stmt = select(Message).where(
            and_(
                Message.conversation_id == conversation_id,
                Message.role == "assistant"
            )
        )
        result = await self.db.execute(stmt)
        messages = result.scalars().all()

        if not messages:
            return 50.0

        quality_scores = []

        for msg in messages:
            score = 100.0

            # 检查回复长度
            if len(msg.content) < 20:
                score -= 30  # 回复过短

            # 检查是否包含错误标记
            if "抱歉" in msg.content or "错误" in msg.content or "失败" in msg.content:
                score -= 20  # 包含错误信息

            # 检查Token效率（输出/输入比）
            if msg.input_tokens and msg.output_tokens:
                token_ratio = msg.output_tokens / msg.input_tokens
                if token_ratio < 0.5:  # 回复过简
                    score -= 10
                elif token_ratio > 5.0:  # 回复过长
                    score -= 10

            quality_scores.append(max(score, 0))

        return sum(quality_scores) / len(quality_scores)

    def _generate_feedback(self, metrics: dict[str, float]) -> tuple[list[str], list[str]]:
        """
        根据指标生成问题列表和改进建议
        """
        issues = []
        suggestions = []

        # 响应时间问题
        if metrics["response_time"] < 60:
            issues.append("响应时间过长")
            suggestions.append("优化LLM调用性能，考虑使用缓存或流式响应")

        # 解决率问题
        if metrics["resolution"] < 60:
            issues.append("对话解决率低")
            suggestions.append("改进知识库内容，增加FAQ覆盖")

        # 满意度问题
        if metrics["satisfaction"] < 60:
            issues.append("用户满意度低")
            suggestions.append("分析用户反馈，调整回复语气和内容")

        # 消息质量问题
        if metrics["message_quality"] < 60:
            issues.append("回复质量不佳")
            suggestions.append("优化提示词工程，提高回复的相关性和完整性")

        if not issues:
            issues.append("无")
            suggestions.append("继续保持良好的服务质量")

        return issues, suggestions

    async def get_quality_summary(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None
    ) -> dict[str, Any]:
        """
        获取质量统计汇总

        Returns:
            {
                "total_conversations": int,
                "avg_quality_score": float,
                "score_distribution": {
                    "excellent": int,  # 90-100
                    "good": int,      # 70-89
                    "fair": int,      # 50-69
                    "poor": int,      # < 50
                },
                "common_issues": list[str],
            }
        """
        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=7)
        if not end_time:
            end_time = datetime.utcnow()

        # 查询对话列表
        stmt = select(Conversation.conversation_id).where(
            and_(
                Conversation.created_at >= start_time,
                Conversation.created_at <= end_time
            )
        )

        if self.tenant_id:
            stmt = stmt.where(Conversation.tenant_id == self.tenant_id)

        result = await self.db.execute(stmt)
        conversation_ids = [row[0] for row in result.fetchall()]

        if not conversation_ids:
            return {
                "total_conversations": 0,
                "avg_quality_score": 0,
                "score_distribution": {
                    "excellent": 0,
                    "good": 0,
                    "fair": 0,
                    "poor": 0,
                },
                "common_issues": [],
            }

        # 评估每个对话
        scores = []
        all_issues = {}

        for conv_id in conversation_ids:
            try:
                evaluation = await self.evaluate_conversation_quality(conv_id)
                scores.append(evaluation["quality_score"])

                # 统计问题
                for issue in evaluation["issues"]:
                    if issue not in all_issues:
                        all_issues[issue] = 0
                    all_issues[issue] += 1
            except Exception as e:
                continue

        # 计算平均分
        avg_score = sum(scores) / len(scores) if scores else 0

        # 分数分布
        distribution = {
            "excellent": sum(1 for s in scores if s >= 90),
            "good": sum(1 for s in scores if 70 <= s < 90),
            "fair": sum(1 for s in scores if 50 <= s < 70),
            "poor": sum(1 for s in scores if s < 50),
        }

        # 最常见的问题（Top 3）
        common_issues = sorted(all_issues.items(), key=lambda x: x[1], reverse=True)[:3]
        common_issues = [issue[0] for issue in common_issues]

        return {
            "total_conversations": len(conversation_ids),
            "avg_quality_score": round(avg_score, 2),
            "score_distribution": distribution,
            "common_issues": common_issues,
        }
