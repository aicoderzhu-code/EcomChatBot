"""
商品数据自动同步服务
将商品、订单数据自动同步到知识库
"""
from datetime import datetime
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from services.rag_enhanced_service import EnhancedRAGService


class DataSyncService:
    """
    数据同步服务

    自动将租户的商品、订单数据同步到知识库，
    实现知识的自动更新和维护
    """

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def sync_products_to_knowledge(
        self,
        products: list[dict],
        batch_size: int = 50
    ) -> dict[str, Any]:
        """
        同步商品数据到知识库

        Args:
            products: 商品列表
            batch_size: 批量大小

        Returns:
            同步结果
        """
        from services.knowledge_service import KnowledgeService

        knowledge_service = KnowledgeService(self.db, self.tenant_id)
        rag_service = EnhancedRAGService(self.db, self.tenant_id)

        created_count = 0
        updated_count = 0
        failed_count = 0

        for product in products:
            try:
                # 构建知识库条目
                knowledge_data = {
                    "title": f"商品: {product.get('name', '未知商品')}",
                    "content": self._format_product_content(product),
                    "category": "product",
                    "source": "auto_sync",
                    "tags": ["商品", product.get("category", "其他")]
                }

                # 检查是否已存在
                existing = await knowledge_service.get_knowledge_by_external_id(
                    external_id=product.get("id")
                )

                if existing:
                    # 更新已有知识
                    await knowledge_service.update_knowledge(
                        knowledge_id=existing.knowledge_id,
                        **knowledge_data
                    )
                    updated_count += 1
                else:
                    # 创建新知识
                    new_knowledge = await knowledge_service.create_knowledge(
                        tenant_id=self.tenant_id,
                        external_id=product.get("id"),
                        **knowledge_data
                    )
                    created_count += 1

            except Exception as e:
                failed_count += 1
                print(f"同步商品失败: {product.get('id')}, error: {e}")

        # 批量索引向量
        all_knowledge = await knowledge_service.list_knowledge(
            category="product",
            limit=1000
        )

        knowledge_ids = [k.knowledge_id for k in all_knowledge]

        if knowledge_ids:
            index_result = await rag_service.batch_index_with_usage(knowledge_ids)
        else:
            index_result = {"total": 0, "success": 0}

        return {
            "total": len(products),
            "created": created_count,
            "updated": updated_count,
            "failed": failed_count,
            "indexed": index_result.get("success", 0)
        }

    def _format_product_content(self, product: dict) -> str:
        """格式化商品内容为文本"""
        parts = [
            f"商品名称: {product.get('name', '未知')}",
            f"价格: ¥{product.get('price', 0)}",
            f"分类: {product.get('category', '其他')}",
        ]

        if product.get('description'):
            parts.append(f"商品描述: {product['description']}")

        if product.get('specifications'):
            parts.append(f"规格参数: {product['specifications']}")

        if product.get('stock', 0) > 0:
            parts.append(f"库存: {product['stock']} 件")
        else:
            parts.append("库存: 暂无库存")

        return "\n".join(parts)

    async def sync_orders_to_knowledge(
        self,
        orders: list[dict],
        batch_size: int = 50
    ) -> dict[str, Any]:
        """
        同步订单数据到知识库

        用于查询订单状态、物流信息等场景

        Args:
            orders: 订单列表
            batch_size: 批量大小

        Returns:
            同步结果
        """
        from services.knowledge_service import KnowledgeService

        knowledge_service = KnowledgeService(self.db, self.tenant_id)

        created_count = 0
        updated_count = 0
        failed_count = 0

        for order in orders:
            try:
                # 构建订单知识
                knowledge_data = {
                    "title": f"订单: {order.get('order_no', '未知订单')}",
                    "content": self._format_order_content(order),
                    "category": "order",
                    "source": "auto_sync",
                    "tags": ["订单", order.get("status", "其他")]
                }

                # 检查是否已存在
                existing = await knowledge_service.get_knowledge_by_external_id(
                    external_id=order.get("id")
                )

                if existing:
                    await knowledge_service.update_knowledge(
                        knowledge_id=existing.knowledge_id,
                        **knowledge_data
                    )
                    updated_count += 1
                else:
                    new_knowledge = await knowledge_service.create_knowledge(
                        tenant_id=self.tenant_id,
                        external_id=order.get("id"),
                        **knowledge_data
                    )
                    created_count += 1

            except Exception as e:
                failed_count += 1
                print(f"同步订单失败: {order.get('id')}, error: {e}")

        return {
            "total": len(orders),
            "created": created_count,
            "updated": updated_count,
            "failed": failed_count
        }

    def _format_order_content(self, order: dict) -> str:
        """格式化订单内容为文本"""
        parts = [
            f"订单号: {order.get('order_no', '未知')}",
            f"订单状态: {order.get('status', '未知')}",
            f"下单时间: {order.get('created_at', '未知')}",
        ]

        if order.get('total_amount'):
            parts.append(f"订单金额: ¥{order['total_amount']}")

        if order.get('items'):
            parts.append("商品清单:")
            for item in order['items']:
                parts.append(f"  - {item.get('product_name', '商品')} x {item.get('quantity', 1)}")

        if order.get('shipping_address'):
            parts.append(f"收货地址: {order['shipping_address']}")

        if order.get('logistics_info'):
            parts.append(f"物流信息: {order['logistics_info']}")

        return "\n".join(parts)

    async def sync_faqs_to_knowledge(
        self,
        faqs: list[dict]
    ) -> dict[str, Any]:
        """
        同步FAQ到知识库

        Args:
            faqs: FAQ列表

        Returns:
            同步结果
        """
        from services.knowledge_service import KnowledgeService

        knowledge_service = KnowledgeService(self.db, self.tenant_id)

        created_count = 0
        failed_count = 0

        for faq in faqs:
            try:
                knowledge_data = {
                    "title": f"FAQ: {faq.get('question', '常见问题')}",
                    "content": f"问题: {faq.get('question')}\n\n回答: {faq.get('answer')}",
                    "category": "faq",
                    "source": "manual",
                    "tags": ["FAQ"] + faq.get("tags", [])
                }

                await knowledge_service.create_knowledge(
                    tenant_id=self.tenant_id,
                    external_id=faq.get("id"),
                    **knowledge_data
                )
                created_count += 1

            except Exception as e:
                failed_count += 1
                print(f"同步FAQ失败: {faq.get('id')}, error: {e}")

        return {
            "total": len(faqs),
            "created": created_count,
            "failed": failed_count
        }
