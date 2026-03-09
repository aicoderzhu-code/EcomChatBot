"""
RAG 检索效果分析服务
"""
import logging
from datetime import datetime, timedelta

from sqlalchemy import and_, cast, Date, Float, func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from models import KnowledgeBase, KnowledgeUsageLog

logger = logging.getLogger(__name__)


class RAGAnalyticsService:
    """RAG 检索效果分析服务"""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def get_retrieval_metrics(
        self, days: int = 30,
    ) -> dict:
        """计算检索效果指标"""
        start_date = datetime.utcnow() - timedelta(days=days)

        # 总查询数
        total_stmt = select(func.count(KnowledgeUsageLog.id)).where(
            and_(
                KnowledgeUsageLog.tenant_id == self.tenant_id,
                KnowledgeUsageLog.created_at >= start_date,
            )
        )
        total_queries = await self.db.scalar(total_stmt) or 0

        # 有匹配结果的查询数（match_score > 0.5）
        hit_stmt = select(func.count(KnowledgeUsageLog.id)).where(
            and_(
                KnowledgeUsageLog.tenant_id == self.tenant_id,
                KnowledgeUsageLog.created_at >= start_date,
                KnowledgeUsageLog.match_score > 0.5,
            )
        )
        hit_count = await self.db.scalar(hit_stmt) or 0

        # 平均匹配分数
        avg_score_stmt = select(func.avg(KnowledgeUsageLog.match_score)).where(
            and_(
                KnowledgeUsageLog.tenant_id == self.tenant_id,
                KnowledgeUsageLog.created_at >= start_date,
                KnowledgeUsageLog.match_score.isnot(None),
            )
        )
        avg_score = await self.db.scalar(avg_score_stmt) or 0

        # 有用/无用反馈统计
        helpful_stmt = select(
            func.count(case((KnowledgeUsageLog.helpful == True, 1))).label("helpful_count"),
            func.count(case((KnowledgeUsageLog.helpful == False, 1))).label("unhelpful_count"),
        ).where(
            and_(
                KnowledgeUsageLog.tenant_id == self.tenant_id,
                KnowledgeUsageLog.created_at >= start_date,
                KnowledgeUsageLog.helpful.isnot(None),
            )
        )
        feedback_result = await self.db.execute(helpful_stmt)
        feedback_row = feedback_result.one()

        hit_rate = (hit_count / total_queries * 100) if total_queries > 0 else 0

        return {
            "total_queries": total_queries,
            "hit_count": hit_count,
            "hit_rate": round(hit_rate, 2),
            "avg_match_score": round(float(avg_score), 4),
            "helpful_count": feedback_row.helpful_count,
            "unhelpful_count": feedback_row.unhelpful_count,
            "days": days,
        }

    async def get_failed_retrievals(
        self, limit: int = 20,
    ) -> list[dict]:
        """获取匹配失败的查询列表"""
        stmt = (
            select(
                KnowledgeUsageLog.query,
                func.count(KnowledgeUsageLog.id).label("count"),
                func.avg(KnowledgeUsageLog.match_score).label("avg_score"),
                func.max(KnowledgeUsageLog.created_at).label("last_queried"),
            )
            .where(
                and_(
                    KnowledgeUsageLog.tenant_id == self.tenant_id,
                    KnowledgeUsageLog.match_score < 0.5,
                )
            )
            .group_by(KnowledgeUsageLog.query)
            .order_by(func.count(KnowledgeUsageLog.id).desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "query": row.query,
                "count": row.count,
                "avg_score": round(float(row.avg_score or 0), 4),
                "last_queried": row.last_queried.isoformat() if row.last_queried else None,
            }
            for row in rows
        ]

    async def get_knowledge_effectiveness(
        self, limit: int = 50,
    ) -> list[dict]:
        """获取知识条目效果排名"""
        stmt = (
            select(
                KnowledgeUsageLog.knowledge_id,
                func.count(KnowledgeUsageLog.id).label("use_count"),
                func.avg(KnowledgeUsageLog.match_score).label("avg_score"),
                func.count(case((KnowledgeUsageLog.helpful == True, 1))).label("helpful_count"),
                func.count(case((KnowledgeUsageLog.helpful == False, 1))).label("unhelpful_count"),
            )
            .where(KnowledgeUsageLog.tenant_id == self.tenant_id)
            .group_by(KnowledgeUsageLog.knowledge_id)
            .order_by(func.count(KnowledgeUsageLog.id).desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        # 获取知识标题
        knowledge_ids = [row.knowledge_id for row in rows]
        if knowledge_ids:
            title_stmt = select(
                KnowledgeBase.knowledge_id, KnowledgeBase.title,
            ).where(
                KnowledgeBase.knowledge_id.in_(knowledge_ids)
            )
            title_result = await self.db.execute(title_stmt)
            title_map = {r.knowledge_id: r.title for r in title_result.all()}
        else:
            title_map = {}

        return [
            {
                "knowledge_id": row.knowledge_id,
                "title": title_map.get(row.knowledge_id, "未知"),
                "use_count": row.use_count,
                "avg_score": round(float(row.avg_score or 0), 4),
                "helpful_count": row.helpful_count,
                "unhelpful_count": row.unhelpful_count,
                "helpful_rate": round(
                    row.helpful_count / (row.helpful_count + row.unhelpful_count) * 100, 2
                ) if (row.helpful_count + row.unhelpful_count) > 0 else None,
            }
            for row in rows
        ]

    async def get_retrieval_trends(
        self, days: int = 30,
    ) -> list[dict]:
        """获取检索效果趋势"""
        start_date = datetime.utcnow() - timedelta(days=days)

        stmt = (
            select(
                cast(KnowledgeUsageLog.created_at, Date).label("date"),
                func.count(KnowledgeUsageLog.id).label("total"),
                func.count(case((KnowledgeUsageLog.match_score > 0.5, 1))).label("hits"),
                func.avg(KnowledgeUsageLog.match_score).label("avg_score"),
            )
            .where(
                and_(
                    KnowledgeUsageLog.tenant_id == self.tenant_id,
                    KnowledgeUsageLog.created_at >= start_date,
                )
            )
            .group_by(cast(KnowledgeUsageLog.created_at, Date))
            .order_by(cast(KnowledgeUsageLog.created_at, Date))
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "date": str(row.date),
                "total": row.total,
                "hits": row.hits,
                "hit_rate": round(row.hits / row.total * 100, 2) if row.total > 0 else 0,
                "avg_score": round(float(row.avg_score or 0), 4),
            }
            for row in rows
        ]
