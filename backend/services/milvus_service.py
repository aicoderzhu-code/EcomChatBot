"""
Milvus 向量数据库服务
"""
from typing import Any

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from core.config import settings


class MilvusService:
    """Milvus 向量数据库服务"""

    COLLECTION_NAME = "knowledge_base"

    def __init__(self, tenant_id: str):
        """
        初始化 Milvus 服务
        
        Args:
            tenant_id: 租户 ID
        """
        self.tenant_id = tenant_id
        self._connect()

    def _connect(self) -> None:
        """连接到 Milvus"""
        try:
            connections.connect(
                alias="default",
                host=settings.milvus_host,
                port=settings.milvus_port,
                user=settings.milvus_user,
                password=settings.milvus_password,
            )
            print(f"✓ 已连接到 Milvus: {settings.milvus_host}:{settings.milvus_port}")
        except Exception as e:
            print(f"✗ 连接 Milvus 失败: {e}")
            raise

    def create_collection_if_not_exists(self) -> Collection:
        """
        创建 Collection（如果不存在）
        
        Returns:
            Collection 实例
        """
        # 检查是否存在
        if utility.has_collection(self.COLLECTION_NAME):
            collection = Collection(self.COLLECTION_NAME)
            collection.load()
            return collection

        # 定义字段
        fields = [
            FieldSchema(
                name="id",
                dtype=DataType.VARCHAR,
                is_primary=True,
                max_length=64,
            ),
            FieldSchema(
                name="tenant_id",
                dtype=DataType.VARCHAR,
                max_length=64,
            ),
            FieldSchema(
                name="knowledge_id",
                dtype=DataType.VARCHAR,
                max_length=64,
            ),
            FieldSchema(
                name="content",
                dtype=DataType.VARCHAR,
                max_length=65535,
            ),
            FieldSchema(
                name="vector",
                dtype=DataType.FLOAT_VECTOR,
                dim=settings.embedding_dimension,
            ),
        ]

        # 创建 Schema
        schema = CollectionSchema(
            fields=fields,
            description="知识库向量 Collection（多租户）",
        )

        # 创建 Collection
        collection = Collection(
            name=self.COLLECTION_NAME,
            schema=schema,
        )

        # 创建索引
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "L2",
            "params": {"nlist": 128},
        }
        collection.create_index(field_name="vector", index_params=index_params)

        # 创建分区（按租户）
        # 注：分区名称只能包含字母、数字和下划线
        partition_name = f"tenant_{self.tenant_id.replace('-', '_')}"
        if not collection.has_partition(partition_name):
            collection.create_partition(partition_name)

        # 加载到内存
        collection.load()

        print(f"✓ 创建 Collection: {self.COLLECTION_NAME}")
        return collection

    async def insert_vectors(
        self,
        knowledge_items: list[dict[str, Any]],
        vectors: list[list[float]],
    ) -> list[str]:
        """
        插入向量
        
        Args:
            knowledge_items: 知识库项列表
            vectors: 对应的向量列表
            
        Returns:
            插入的 ID 列表
        """
        collection = self.create_collection_if_not_exists()

        # 准备数据
        ids = [item["id"] for item in knowledge_items]
        tenant_ids = [self.tenant_id] * len(knowledge_items)
        knowledge_ids = [item["knowledge_id"] for item in knowledge_items]
        contents = [item["content"][:65535] for item in knowledge_items]  # 限制长度

        # 插入数据到租户分区
        partition_name = f"tenant_{self.tenant_id.replace('-', '_')}"

        entities = [
            ids,
            tenant_ids,
            knowledge_ids,
            contents,
            vectors,
        ]

        collection.insert(entities, partition_name=partition_name)
        collection.flush()

        print(f"✓ 插入 {len(ids)} 条向量到 Milvus")
        return ids

    async def search_vectors(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filter_expr: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        搜索相似向量
        
        Args:
            query_vector: 查询向量
            top_k: 返回结果数量
            filter_expr: 过滤表达式
            
        Returns:
            搜索结果列表
        """
        collection = self.create_collection_if_not_exists()

        # 搜索参数
        search_params = {
            "metric_type": "L2",
            "params": {"nprobe": 10},
        }

        # 只搜索当前租户的分区
        partition_name = f"tenant_{self.tenant_id.replace('-', '_')}"

        # 搜索
        results = collection.search(
            data=[query_vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            expr=filter_expr,
            output_fields=["knowledge_id", "content", "tenant_id"],
            partition_names=[partition_name],
        )

        # 格式化结果
        formatted_results = []
        if results:
            for hits in results:
                for hit in hits:
                    formatted_results.append(
                        {
                            "id": hit.id,
                            "knowledge_id": hit.entity.get("knowledge_id"),
                            "content": hit.entity.get("content"),
                            "score": hit.distance,  # L2 距离（越小越相似）
                            "similarity": 1 / (1 + hit.distance),  # 转换为相似度
                        }
                    )

        return formatted_results

    async def delete_vectors(self, knowledge_ids: list[str]) -> int:
        """
        删除向量
        
        Args:
            knowledge_ids: 知识库 ID 列表
            
        Returns:
            删除的数量
        """
        collection = self.create_collection_if_not_exists()

        # 构建删除表达式
        ids_str = ", ".join([f"'{kid}'" for kid in knowledge_ids])
        expr = f"knowledge_id in [{ids_str}] and tenant_id == '{self.tenant_id}'"

        # 删除
        collection.delete(expr)
        collection.flush()

        print(f"✓ 删除 {len(knowledge_ids)} 条向量")
        return len(knowledge_ids)

    def get_collection_stats(self) -> dict[str, Any]:
        """
        获取 Collection 统计信息
        
        Returns:
            统计信息
        """
        if not utility.has_collection(self.COLLECTION_NAME):
            return {
                "exists": False,
                "name": self.COLLECTION_NAME,
            }

        collection = Collection(self.COLLECTION_NAME)

        # 获取租户分区统计
        partition_name = f"tenant_{self.tenant_id.replace('-', '_')}"
        partition_stats = {}

        if collection.has_partition(partition_name):
            partition = collection.partition(partition_name)
            partition_stats = {
                "name": partition_name,
                "num_entities": partition.num_entities,
            }

        return {
            "exists": True,
            "name": self.COLLECTION_NAME,
            "num_entities": collection.num_entities,
            "tenant_partition": partition_stats,
        }

    @staticmethod
    def disconnect() -> None:
        """断开连接"""
        try:
            connections.disconnect(alias="default")
            print("✓ 已断开 Milvus 连接")
        except Exception as e:
            print(f"断开 Milvus 连接失败: {e}")
